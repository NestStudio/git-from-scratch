use anyhow::{Context, Result, bail};

use crate::utils::*;

pub fn process_write_tree() -> Result<()> {
    let git_dir = find_git_dir().context("Unable to find .git")?;
    let mut current_working_dir = git_dir.clone();
    current_working_dir.pop();
    if !current_working_dir.is_dir() {
        bail!("No file/folder to write tree")
    }

    let root_tree_hash = recurse_working_dir_write(current_working_dir)?;
    println!("Tree written successfully at hash: {root_tree_hash}");

    Ok(())
}
