use anyhow::{Context, Result};

use crate::commands::HashListArgs;
use crate::utils::*;

pub fn process_hash_list(hash_list_args: HashListArgs) -> Result<()> {
    let (payload_to_hash, hash) = hash_blob(&hash_list_args.file)?;
    let mut git_dir = find_git_dir().context("Unable to find .git")?;
    create_object_dir(&mut git_dir, &hash)?;
    write_payload(&mut git_dir, &hash, &payload_to_hash)?;

    println!("Hash: {hash}");
    Ok(())
}
