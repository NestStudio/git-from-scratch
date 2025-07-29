use std::{fs::File, io::Read};

use anyhow::{Result, bail};
use flate2::read::ZlibDecoder;

use crate::{commands::CatFileArgs, utils::find_git_dir};

pub fn process_cat_file(cat_file_args: CatFileArgs) -> Result<()> {
    let hash = cat_file_args.hash;
    println!("Hash length: {:?}", hash.len());
    if hash.len() != 40 {
        bail!("Invalid hash passed");
    }

    let folder_name = &hash[0..2];
    let file_name = &hash[2..];

    let git_dir = find_git_dir();
    if git_dir.is_none() {
        bail!("Unable to find .git");
    }
    let mut git_dir = git_dir.unwrap();
    git_dir.push("objects");
    git_dir.push(folder_name);
    git_dir.push(file_name);

    if !git_dir.exists() {
        bail!("Object not found");
    }

    let mut file = File::open(&git_dir)?;
    let mut buffer = vec![];
    file.read_to_end(&mut buffer)?;

    let mut decoder = ZlibDecoder::new(buffer.as_slice());
    let mut decompressed_data = Vec::new();
    decoder.read_to_end(&mut decompressed_data)?;

    let null_byte_position = decompressed_data.iter().position(|&byte| byte == 0);
    if null_byte_position.is_none() {
        bail!("Blob data corrupted.");
    }
    let null_byte_position = null_byte_position.unwrap();
    let (header_bytes, data) = decompressed_data.split_at(null_byte_position + 1);
    let header = std::str::from_utf8(header_bytes)?;

    println!("Header: {:?}", header);
    match std::str::from_utf8(data) {
        Ok(data) => println!("Parsed data: {data}"),
        Err(_) => println!("Data not UTF-8. Raw bytes: {:?}", data),
    }

    Ok(())
}
