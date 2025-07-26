use clap::{Parser, Subcommand};

pub mod init;
pub use init::*;

#[derive(Parser)]
#[command(name = "sgit", version, about, long_about = None)]
pub struct GitCli {
    #[command(subcommand)]
    pub command: Subcommands,
}

#[derive(Subcommand)]
pub enum Subcommands {
    Init,
}
