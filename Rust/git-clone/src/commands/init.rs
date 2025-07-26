use anyhow::{Result, bail};
use std::{
    env::current_dir,
    fs::{File, create_dir_all},
    io::Write,
};

pub fn process_git_init() -> Result<()> {
    let mut git_dir = current_dir()?;
    git_dir.push(".git");

    if git_dir.exists() {
        // No need to proceed further
        bail!(".git already exists");
    } else {
        // Create .git root folder
        create_dir_all(&git_dir)?;

        // .git/HEAD
        git_dir.push("HEAD");
        let mut head = File::create(&git_dir)?;
        writeln!(head, "ref: refs/heads/master")?;

        // .git/objects/
        git_dir.pop();
        git_dir.push("objects");
        create_dir_all(&git_dir)?;

        // .git/refs
        git_dir.pop();
        git_dir.push("refs");
        create_dir_all(&git_dir)?;

        // .git/refs/heads
        git_dir.push("heads");
        create_dir_all(&git_dir)?;

        // .git/refs/tags
        git_dir.pop();
        git_dir.push("tags");
        create_dir_all(&git_dir)?;
    }

    Ok(())
}
