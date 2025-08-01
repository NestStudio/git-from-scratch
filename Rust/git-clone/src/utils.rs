use std::{env::current_dir, fs::DirEntry, io::Write, os::unix::fs::MetadataExt, path::PathBuf};

use anyhow::{Context, Result, bail};
use flate2::{Compression, write::ZlibEncoder};
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

pub fn recurse_working_dir(path: PathBuf) -> Result<String> {
    let mut directory_contents = std::fs::read_dir(&path)?
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
            let subtree_hash = recurse_working_dir(content_path)?;
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
    let data = std::fs::read(file_path)?;
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
    std::fs::create_dir_all(&git_dir)?;

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
    let mut file = std::fs::File::create(&git_dir)?;
    file.write_all(&compressed_data)?;

    Ok(())
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
    let metadata = std::fs::metadata(path)?;
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
