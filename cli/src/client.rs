use anyhow::{bail, Context, Result};
use reqwest::blocking::{Client, RequestBuilder, Response};
use reqwest::StatusCode;
use serde_json::Value;

use crate::config::Config;

pub struct ApiClient {
    base: String,
    api_key: Option<String>,
    http: Client,
}

impl ApiClient {
    pub fn new(config: &Config) -> Self {
        Self {
            base: config.url.trim_end_matches('/').to_string(),
            api_key: config.api_key.clone(),
            http: Client::new(),
        }
    }

    fn send(&self, request: RequestBuilder) -> Result<Response> {
        let request = if let Some(key) = &self.api_key {
            request.header("x-api-key", key)
        } else {
            request
        };
        let response = request.send().context("HTTP request failed")?;
        if !response.status().is_success() {
            let status = response.status();
            let body = response.text().unwrap_or_default();
            bail!("HTTP {}: {}", status.as_u16(), body);
        }
        Ok(response)
    }

    pub fn get(&self, path: &str, query: &[(&str, String)]) -> Result<Value> {
        let url = format!("{}{}", self.base, path);
        let response = self.send(self.http.get(url).query(query))?;
        if response.status() == StatusCode::NO_CONTENT {
            return Ok(Value::Null);
        }
        Ok(response.json()?)
    }

    pub fn post(&self, path: &str, body: &Value) -> Result<Value> {
        let url = format!("{}{}", self.base, path);
        let response = self.send(self.http.post(url).json(body))?;
        if response.status() == StatusCode::NO_CONTENT {
            return Ok(Value::Null);
        }
        Ok(response.json()?)
    }

    pub fn patch(&self, path: &str, body: &Value) -> Result<Value> {
        let url = format!("{}{}", self.base, path);
        let response = self.send(self.http.patch(url).json(body))?;
        Ok(response.json()?)
    }

    pub fn delete(&self, path: &str) -> Result<()> {
        let url = format!("{}{}", self.base, path);
        self.send(self.http.delete(url))?;
        Ok(())
    }
}
