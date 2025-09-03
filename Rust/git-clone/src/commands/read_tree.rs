use std::env::current_dir;

use crate::{commands::ReadTreeArgs, utils::recurse_working_dir_read};
use anyhow::Result;

pub fn process_read_tree(read_tree_args: ReadTreeArgs) -> Result<()> {
    let hash = read_tree_args.hash;
    recurse_working_dir_read(&hash, &current_dir()?)?;
    println!("Tree hash reading done!!");

    Ok(())
}
