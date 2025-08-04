use anyhow::Result;

use crate::{commands::CatFileArgs, utils::read_payload_from_hash};

pub fn process_cat_file(cat_file_args: CatFileArgs) -> Result<()> {
    let hash = cat_file_args.hash;
    let (decompressed_data, null_byte_position) = read_payload_from_hash(&hash)?;

    let (header_bytes, data) = decompressed_data.split_at(null_byte_position + 1);
    let header = std::str::from_utf8(header_bytes)?;

    println!("Header: {:?}", header);
    match std::str::from_utf8(data) {
        Ok(data) => println!("Parsed data: {data}"),
        Err(_) => println!("Data not UTF-8. Raw bytes: {:?}", data),
    }

    Ok(())
}
