mod client;
mod commands;
mod config;

use clap::{Args, Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(name = "nxflow", version, about = "NexusFlow data center inventory CLI")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Subcommand, Debug)]
pub enum Command {
    /// Manage CLI configuration
    Config {
        #[command(subcommand)]
        command: ConfigCommand,
    },
    /// Resource CRUD operations
    Resource {
        #[command(subcommand)]
        command: ResourceCommand,
    },
    /// Tokenized search, e.g. `status:active tag:prod`
    Search {
        query: String,
        #[arg(long, default_value_t = 50)]
        limit: usize,
        #[arg(long, default_value_t = 0)]
        offset: usize,
    },
    /// Show the audit history of a resource
    History {
        id: String,
        #[arg(long, default_value_t = 100)]
        limit: usize,
    },
    /// Relationship operations
    Rel {
        #[command(subcommand)]
        command: RelCommand,
    },
    /// Bulk import resources from a JSON file
    Import { file: PathBuf },
    /// Export resources as JSON
    Export {
        #[arg(long)]
        q: Option<String>,
    },
}

#[derive(Subcommand, Debug)]
pub enum ConfigCommand {
    Init {
        #[arg(long)]
        url: String,
        #[arg(long)]
        api_key: Option<String>,
    },
    Show,
}

#[derive(Subcommand, Debug)]
pub enum ResourceCommand {
    List {
        #[arg(long)]
        q: Option<String>,
        #[arg(long, default_value_t = 50)]
        limit: usize,
        #[arg(long, default_value_t = 0)]
        offset: usize,
    },
    Get {
        id: String,
    },
    Create {
        #[command(flatten)]
        fields: ResourceFields,
        #[arg(long)]
        file: Option<PathBuf>,
    },
    Update {
        id: String,
        #[arg(long)]
        version: i64,
        #[command(flatten)]
        fields: ResourceFields,
        #[arg(long)]
        file: Option<PathBuf>,
    },
    Delete {
        id: String,
    },
}

#[derive(Args, Debug, Default)]
pub struct ResourceFields {
    #[arg(long = "type")]
    pub resource_type: Option<String>,
    #[arg(long)]
    pub name: Option<String>,
    #[arg(long)]
    pub status: Option<String>,
    #[arg(long)]
    pub location: Option<String>,
    #[arg(long = "tag")]
    pub tags: Vec<String>,
    #[arg(long = "attr", help = "key=value, value parsed as JSON when possible")]
    pub attrs: Vec<String>,
    #[arg(long = "meta")]
    pub meta: Vec<String>,
}

#[derive(Subcommand, Debug)]
pub enum RelCommand {
    Add {
        #[arg(long)]
        source: String,
        #[arg(long)]
        target: String,
        #[arg(long = "type")]
        rel_type: String,
        #[arg(long = "meta")]
        meta: Vec<String>,
    },
    List {
        id: String,
    },
    Rm {
        id: String,
    },
}

fn main() {
    let cli = Cli::parse();
    if let Err(error) = commands::run(cli) {
        eprintln!("error: {error:#}");
        std::process::exit(1);
    }
}
