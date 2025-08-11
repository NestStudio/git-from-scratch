use anyhow::{Result, bail};
use sha1::{Digest, Sha1};

use crate::{
    commands::CommitArgs,
    utils::{build_commit_payload, create_obj_write_payload, is_valid_name},
};
use validator::ValidateEmail;

pub fn process_commit(commit_args: CommitArgs) -> Result<()> {
    let CommitArgs {
        name,
        email,
        hash,
        message,
    } = commit_args;

    if !is_valid_name(&name) {
        bail!("Invalid name");
    }

    if !email.validate_email() {
        bail!("Invalid email");
    }

    let commit_payload = build_commit_payload(&hash, &name, &email, &message);
    let commit_header = format!("commit {}\0", commit_payload.as_bytes().len());
    let commit_message = commit_header + &commit_payload;
    let commit_message_bytes = commit_message.as_bytes();

    let commit_hash = hex::encode(Sha1::digest(commit_message_bytes));
    create_obj_write_payload(commit_message_bytes, &commit_hash)?;

    println!("Commit success at hash {:?}", commit_hash);
    Ok(())
}
