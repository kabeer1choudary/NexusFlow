use anyhow::{bail, Context, Result};
use serde_json::{json, Map, Value};
use std::fs;
use std::path::Path;

use crate::client::ApiClient;
use crate::config::{config_path, Config};
use crate::{
    Cli, Command, ConfigCommand, RelCommand, ResourceCommand, ResourceFields,
};

pub fn run(cli: Cli) -> Result<()> {
    match cli.command {
        Command::Config { command } => match command {
            ConfigCommand::Init { url, api_key } => {
                Config { url, api_key }.save()?;
                println!("wrote {}", config_path().display());
                Ok(())
            }
            ConfigCommand::Show => {
                let config = Config::load()?;
                println!("{}", toml::to_string_pretty(&config)?);
                Ok(())
            }
        },
        Command::Resource { command } => resource(&client()?, command),
        Command::Search {
            query,
            limit,
            offset,
        } => {
            let params = vec![
                ("q", query),
                ("limit", limit.to_string()),
                ("offset", offset.to_string()),
            ];
            print_json(&client()?.get("/api/v1/resources", &params)?)
        }
        Command::History { id, limit } => {
            let params = vec![("limit", limit.to_string())];
            print_json(
                &client()?.get(&format!("/api/v1/resources/{id}/history"), &params)?,
            )
        }
        Command::Rel { command } => relationship(&client()?, command),
        Command::Import { file } => {
            let body = read_json(&file)?;
            print_json(&client()?.post("/api/v1/import", &body)?)
        }
        Command::Export { q } => {
            let params: Vec<(&str, String)> = q.map(|q| vec![("q", q)]).unwrap_or_default();
            print_json(&client()?.get("/api/v1/export", &params)?)
        }
    }
}

fn client() -> Result<ApiClient> {
    Ok(ApiClient::new(&Config::load()?))
}

fn resource(client: &ApiClient, command: ResourceCommand) -> Result<()> {
    match command {
        ResourceCommand::List { q, limit, offset } => {
            let mut params = vec![
                ("limit", limit.to_string()),
                ("offset", offset.to_string()),
            ];
            if let Some(q) = q {
                params.push(("q", q));
            }
            print_json(&client.get("/api/v1/resources", &params)?)
        }
        ResourceCommand::Get { id } => {
            print_json(&client.get(&format!("/api/v1/resources/{id}"), &[])?)
        }
        ResourceCommand::Create { fields, file } => {
            let body = match file {
                Some(path) => read_json(&path)?,
                None => {
                    let map = fields_to_map(&fields);
                    if !map.contains_key("type") || !map.contains_key("name") {
                        bail!("--type and --name are required when no --file is given");
                    }
                    Value::Object(map)
                }
            };
            print_json(&client.post("/api/v1/resources", &body)?)
        }
        ResourceCommand::Update {
            id,
            version,
            fields,
            file,
        } => {
            let mut body = match file {
                Some(path) => read_json(&path)?,
                None => Value::Object(Map::new()),
            };
            let map = match &mut body {
                Value::Object(map) => map,
                _ => bail!("--file must contain a JSON object"),
            };
            for (key, value) in fields_to_map(&fields) {
                map.insert(key, value);
            }
            map.insert("version".to_string(), json!(version));
            print_json(&client.patch(&format!("/api/v1/resources/{id}"), &body)?)
        }
        ResourceCommand::Delete { id } => {
            client.delete(&format!("/api/v1/resources/{id}"))?;
            println!("deleted {id}");
            Ok(())
        }
    }
}

fn relationship(client: &ApiClient, command: RelCommand) -> Result<()> {
    match command {
        RelCommand::Add {
            source,
            target,
            rel_type,
            meta,
        } => {
            let metadata = kv_map(&meta);
            let body = json!({
                "source_id": source,
                "target_id": target,
                "rel_type": rel_type,
                "metadata": Value::Object(metadata),
            });
            print_json(&client.post("/api/v1/relationships", &body)?)
        }
        RelCommand::List { id } => {
            print_json(&client.get(&format!("/api/v1/resources/{id}/relationships"), &[])?)
        }
        RelCommand::Rm { id } => {
            client.delete(&format!("/api/v1/relationships/{id}"))?;
            println!("deleted relationship {id}");
            Ok(())
        }
    }
}

fn fields_to_map(fields: &ResourceFields) -> Map<String, Value> {
    let mut map = Map::new();
    if let Some(value) = &fields.resource_type {
        map.insert("type".to_string(), json!(value));
    }
    if let Some(value) = &fields.name {
        map.insert("name".to_string(), json!(value));
    }
    if let Some(value) = &fields.status {
        map.insert("status".to_string(), json!(value));
    }
    if let Some(value) = &fields.location {
        map.insert("location".to_string(), json!(value));
    }
    if !fields.tags.is_empty() {
        map.insert("tags".to_string(), json!(fields.tags));
    }
    let attributes = kv_map(&fields.attrs);
    if !attributes.is_empty() {
        map.insert("attributes".to_string(), Value::Object(attributes));
    }
    let metadata = kv_map(&fields.meta);
    if !metadata.is_empty() {
        map.insert("metadata".to_string(), Value::Object(metadata));
    }
    map
}

fn kv_map(items: &[String]) -> Map<String, Value> {
    items
        .iter()
        .filter_map(|item| item.split_once('='))
        .map(|(key, value)| (key.to_string(), parse_value(value)))
        .collect()
}

fn parse_value(value: &str) -> Value {
    serde_json::from_str(value).unwrap_or_else(|_| Value::String(value.to_string()))
}

fn read_json(path: &Path) -> Result<Value> {
    let text = fs::read_to_string(path)
        .with_context(|| format!("read {}", path.display()))?;
    Ok(serde_json::from_str(&text)?)
}

fn print_json(value: &Value) -> Result<()> {
    println!("{}", serde_json::to_string_pretty(value)?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::parse_value;

    #[test]
    fn parses_numbers_and_strings() {
        assert!(parse_value("450").is_number());
        assert!(parse_value("true").is_boolean());
        assert_eq!(parse_value("A-1042"), serde_json::json!("A-1042"));
    }
}
