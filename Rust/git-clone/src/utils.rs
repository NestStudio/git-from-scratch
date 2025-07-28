use std::{env::current_dir, path::PathBuf};

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
