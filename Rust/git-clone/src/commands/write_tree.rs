use anyhow::{Context, Result, bail};

use crate::utils::{find_git_dir, recurse_working_dir};

pub fn process_write_tree() -> Result<()> {
    let git_dir = find_git_dir().context("Unable to find .git")?;
    let mut current_working_dir = git_dir.clone();
    current_working_dir.pop();
    if !current_working_dir.is_dir() {
        bail!("No file/folder to write tree")
    }

    recurse_working_dir(current_working_dir)?;

    Ok(())
}
