use anyhow::{Result, bail};
use flate2::{Compression, write::ZlibEncoder};
use sha1::{Digest, Sha1};
use std::fs::File;
use std::{fs, io::Write};

use crate::commands::HashListArgs;
use crate::utils::find_git_dir;

pub fn process_hash_list(hash_list_args: HashListArgs) -> Result<()> {
    let data = fs::read(hash_list_args.file)?;
    let header = format!("blob {}\0", data.len());
    let payload_to_hash = [header.as_bytes(), &data].concat();
    let hash = hex::encode(Sha1::digest(&payload_to_hash));

    println!("Hash: {hash}");

    let git_dir = find_git_dir();
    if git_dir.is_none() {
        bail!("Unable to find .git");
    }
    let mut git_dir = git_dir.unwrap();
    let object_dir_name = &hash[0..2];
    git_dir.push("objects");
    git_dir.push(object_dir_name);

    if !git_dir.exists() {
        println!("Compressing hash data");
        fs::create_dir(&git_dir)?;

        let file_name = &hash[2..];
        git_dir.push(file_name);
        let mut encoder = ZlibEncoder::new(Vec::new(), Compression::default());
        encoder.write_all(&payload_to_hash)?;
        let compressed_data = encoder.finish()?;
        let mut file = File::create(&git_dir)?;
        file.write_all(&compressed_data)?;
    }

    Ok(())
}
