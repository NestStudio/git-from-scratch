use std::{
    env::current_dir,
    fs::{self, DirEntry, File},
    io::{Read, Write},
    os::unix::fs::MetadataExt,
    path::PathBuf,
};

use anyhow::{Context, Result, bail};
use flate2::{Compression, read::ZlibDecoder, write::ZlibEncoder};
use sha1::{Digest, Sha1};

pub fn find_git_dir() -> Option<PathBuf> {
    let mut dir = current_dir().ok()?;
    loop {
        let git_dir = dir.join(".git");
        if git_dir.exists() {
            return Some(git_dir);
        }

        if !dir.pop() {
            break;
        }
    }

    None
}

pub fn recurse_working_dir_read(hash: &str, path: &PathBuf) -> Result<()> {
    let (decompressed_data, null_byte_position) = read_payload_from_hash(&hash)?;
    let (_header_bytes, data) = decompressed_data.split_at(null_byte_position + 1);

    let mut checkpoint = 0usize;
    let mut position = 0usize;
    while position < data.len() {
        if data[position] == 0 {
            let tree_entry_header = std::str::from_utf8(&data[checkpoint..=position])?
                .trim_end_matches('\0')
                .split_ascii_whitespace()
                .collect::<Vec<&str>>();
            if tree_entry_header.len() != 2 {
                bail!("Invalid Tree entry header");
            }

            let (mode, content_name) = (tree_entry_header[0], tree_entry_header[1]);
            let content_path = path.join(content_name);

            let tree_entry_hash = hex::encode(&data[position + 1..position + 21]);

            match mode {
                "40000" => {
                    if content_path.exists() {
                        fs::remove_dir_all(&content_path)?;
                    }
                    fs::create_dir_all(&content_path)?;
                    recurse_working_dir_read(&tree_entry_hash, &content_path)?
                }
                "100644" | "100755" => {
                    let (decompressed_data, null_byte_position) =
                        read_payload_from_hash(&tree_entry_hash)?;
                    let (_, data) = decompressed_data.split_at(null_byte_position + 1);
                    let mut file = File::create(&content_path)?;
                    file.write_all(data)?;
                }
                _ => bail!("Invalid mode detected. Tree entry corrupted"),
            }

            position += 21; // Raw hash bytes is 20 in length + next byte after null byte (/0)
            checkpoint = position;
            continue;
        }

        position += 1;
    }
    Ok(())
}

pub fn recurse_working_dir_write(path: PathBuf) -> Result<String> {
    let mut directory_contents = fs::read_dir(&path)?
        .filter_map(Result::ok)
        .collect::<Vec<DirEntry>>();
    directory_contents.sort_by_key(|content| content.file_name());

    let mut tree_bytes: Vec<u8> = vec![];

    for content in directory_contents {
        let content_path = content.path();
        let content_file = content.file_name();

        if content_file == ".git" {
            continue;
        }

        if content_path.is_dir() {
            let subtree_hash = recurse_working_dir_write(content_path)?;
            tree_bytes.append(&mut build_tree_entry(&content, &subtree_hash)?);
        } else {
            let (payload, hash) = hash_blob(&content_path)?;
            create_obj_write_payload(&payload, &hash)?;
            tree_bytes.append(&mut build_tree_entry(&content, &hash)?);
        }
    }

    let tree_header = format!("tree {}\0", tree_bytes.len());
    let tree_payload = [tree_header.as_bytes(), &tree_bytes].concat();
    let tree_hash = hex::encode(Sha1::digest(&tree_payload));
    create_obj_write_payload(&tree_payload, &tree_hash)?;

    Ok(tree_hash)
}

pub fn hash_blob(file_path: &PathBuf) -> Result<(Vec<u8>, String)> {
    let data = fs::read(file_path)?;
    let header = format!("blob {}\0", data.len());
    let payload_to_hash = [header.as_bytes(), &data].concat();
    let hash = hex::encode(Sha1::digest(&payload_to_hash));
    Ok((payload_to_hash, hash))
}

pub fn compress_data(payload: &[u8]) -> Result<Vec<u8>> {
    let mut encoder = ZlibEncoder::new(Vec::new(), Compression::default());
    encoder.write_all(payload)?;
    encoder.finish().context("Failed to compress data")
}

pub fn create_obj_write_payload(payload: &[u8], hash: &str) -> Result<()> {
    let mut git_dir = find_git_dir().context("Unable to find .git")?;
    create_object_dir(&mut git_dir, &hash)?;
    write_payload(&mut git_dir, &hash, &payload)?;
    Ok(())
}

pub fn create_object_dir(git_dir: &mut PathBuf, hash: &str) -> Result<()> {
    let object_dir_name = &hash[0..2];
    git_dir.push("objects");
    git_dir.push(object_dir_name);
    fs::create_dir_all(&git_dir)?;

    Ok(())
}

pub fn write_payload(git_dir: &mut PathBuf, hash: &str, payload: &[u8]) -> Result<()> {
    let dir_name = git_dir.file_name().context("Unable to fetch file name")?;
    if dir_name.len() != 2 {
        bail!("Invalid object directory")
    }

    let file_name = &hash[2..];
    git_dir.push(file_name);
    let compressed_data = compress_data(payload)?;
    let mut file = fs::File::create(&git_dir)?;
    file.write_all(&compressed_data)?;

    Ok(())
}

pub fn read_payload_from_hash(hash: &str) -> Result<(Vec<u8>, usize)> {
    if hash.len() != 40 {
        bail!("Invalid hash passed");
    }

    let buffer = find_file_git_objects(&hash)?;
    let decompressed_data = decompress_buffer(&buffer)?;

    let null_byte_position = decompressed_data
        .iter()
        .position(|&byte| byte == 0)
        .context("Data is corrupted")?;

    Ok((decompressed_data, null_byte_position))
}

pub fn build_tree_entry(content: &DirEntry, hash: &str) -> Result<Vec<u8>> {
    let mode = parse_git_mode(&content.path())?;
    let file_name = content
        .file_name()
        .to_str()
        .context("Failed to convert file/folder name as string")?
        .to_owned();
    let raw_hash_bytes = hex::decode(&hash)?;

    Ok([
        format!("{mode} {}\0", file_name).as_bytes(),
        &raw_hash_bytes,
    ]
    .concat())
}

pub fn parse_git_mode(path: &PathBuf) -> Result<String> {
    let metadata = fs::metadata(path)?;
    let mode = metadata.mode();
    let file_type = metadata.file_type();

    Ok(if file_type.is_dir() {
        "40000".to_owned()
    } else if file_type.is_file() {
        if mode & 0o001 == 1 {
            "100755".to_owned()
        } else {
            "100644".to_owned()
        }
    } else {
        bail!("Invalid file type")
    })
}

pub fn find_file_git_objects(hash: &str) -> Result<Vec<u8>> {
    let mut git_dir = find_git_dir().context("Unable to find .git")?;
    let folder_name = &hash[0..2];
    let file_name = &hash[2..];

    git_dir.push("objects");
    git_dir.push(folder_name);
    git_dir.push(file_name);

    if !git_dir.exists() {
        bail!("Object not found");
    }

    let mut file = fs::File::open(&git_dir)?;
    let mut buffer = vec![];
    file.read_to_end(&mut buffer)?;

    Ok(buffer)
}

pub fn decompress_buffer(buffer: &[u8]) -> Result<Vec<u8>> {
    let mut decoder = ZlibDecoder::new(buffer);
    let mut decompressed_data = Vec::new();
    decoder.read_to_end(&mut decompressed_data)?;

    Ok(decompressed_data)
}
