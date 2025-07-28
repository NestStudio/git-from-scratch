use anyhow::Result;
use sha1::{Digest, Sha1};
use std::fs;

use crate::commands::HashListArgs;

pub fn process_hash_list(hash_list_args: HashListArgs) -> Result<()> {
    let data = fs::read(hash_list_args.file)?;
    let header = format!("blob {}\0", data.len());
    let payload_to_hash = [header.as_bytes(), &data].concat();
    let hash = Sha1::digest(&payload_to_hash);
    println!("Hash: {}", hex::encode(hash));

    Ok(())
}
