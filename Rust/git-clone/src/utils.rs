use std::{env::current_dir, io::Write, path::PathBuf};

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

pub fn recurse_working_dir(path: PathBuf) -> Result<()> {
    let directory_contents = std::fs::read_dir(&path)?;
    for content in directory_contents {
        let content = content?;
        if content.file_name() == ".git" {
            continue;
        }

        let content_path = content.path();

        if content_path.is_dir() {
            recurse_working_dir(content_path)?;
        } else {
            let (payload, hash) = hash_blob(&content_path)?;
            println!("Path is a file: {:?} with hash: {hash}", content_path);
            let mut git_dir = find_git_dir().context("Unable to find .git")?;
            create_object_dir(&mut git_dir, &hash)?;
            write_payload(&mut git_dir, &hash, &payload)?;
        }
    }
    Ok(())
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
