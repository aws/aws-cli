use super::{
    AddressingStyle, CACERT_ENTRY_NAME, ChecksumMode, ClientConfig, MemoryLimit, Persona,
    RetryMode, Trust,
};
use crate::proxy;

trait Record: FnMut(&[u8]) {
    fn text(&mut self, line: &str) {
        self(line.as_bytes());
    }
}
impl<F: FnMut(&[u8])> Record for F {}

impl ClientConfig {
    pub fn log_resolved(&self, proxy: proxy::Environment<'_>, mut record: impl FnMut(&[u8])) {
        if let Some(persona) = &self.persona {
            let name = match persona.value {
                Persona::CrtPreferred => "crt_preferred",
                Persona::Tuned => "tuned",
                Persona::NewlyEligible => "newly_eligible",
            };
            record.text(&format!(
                "Transfer persona: {name} (from {})",
                persona.source
            ));
        }
        record.text(&format!(
            "Throughput target: {} Gbps (from {})",
            self.target_gbps.value, self.target_gbps.source
        ));
        if self.persona.is_some() {
            self.log_transfer(&mut record);
            for (name, mode) in [
                ("Request checksum calculation", &self.request_checksum),
                ("Response checksum validation", &self.response_checksum),
            ] {
                let value = match mode.value {
                    ChecksumMode::WhenRequired => "when_required",
                    ChecksumMode::WhenSupported => "when_supported",
                };
                record.text(&format!("{name}: {value} (from {})", mode.source));
            }
        }
        self.log_network(&mut record);
        self.log_endpoint(&mut record);
        if proxy.has_bypass_list() {
            let variable = if proxy.no_proxy.lower.is_some() {
                "no_proxy"
            } else {
                "NO_PROXY"
            };
            record.text(&format!(
                "Proxy bypass list: set (from environment variable {variable})"
            ));
        } else {
            record.text("Proxy bypass list: none");
        }
        for (name, value) in [
            ("User agent app id", &self.app_id),
            ("User agent execution environment", &self.execution_env),
        ] {
            if let Some(value) = value {
                let mut line = format!("{name}: ").into_bytes();
                line.extend_from_slice(&value.value);
                line.extend_from_slice(format!(" (from {})", value.source).as_bytes());
                record(&line);
            }
        }
    }

    fn log_transfer(&self, record: &mut impl Record) {
        let part_size = if self.part_size.value == 0 {
            "CRT dynamic".into()
        } else {
            format!("{} bytes", self.part_size.value)
        };
        record.text(&format!(
            "Part size: {part_size} (from {})",
            self.part_size.source
        ));
        if let Some(threshold) = &self.multipart_threshold {
            record.text(&format!(
                "Multipart threshold: {} bytes (from {})",
                threshold.value, threshold.source
            ));
        } else {
            record.text("Multipart threshold: CRT default (from default)");
        }
        if let Some(cap) = &self.max_connections {
            record.text(&format!(
                "Connection cap: {} (from {})",
                cap.value, cap.source
            ));
        } else {
            record.text("Connection cap: none (from default)");
        }
        self.log_file_io(record);
        let tier = if self.memory_limit.value == MemoryLimit::Tier {
            ", the target's tier"
        } else {
            ""
        };
        record.text(&format!(
            "Memory limit: {} bytes{tier} (from {})",
            self.memory_bytes(),
            self.memory_limit.source
        ));
    }

    fn log_file_io(&self, record: &mut impl Record) {
        if self.should_stream.is_none()
            && self.disk_throughput_gbps.is_none()
            && self.direct_io.is_none()
        {
            record.text("File I/O options: CRT default (from default)");
        }
        if let Some(value) = &self.should_stream {
            record.text(&format!(
                "File I/O should_stream: {} (from {})",
                value.value, value.source
            ));
        }
        if let Some(value) = &self.disk_throughput_gbps {
            record.text(&format!(
                "File I/O disk throughput: {} Gbps (from {})",
                value.value, value.source
            ));
        }
        if let Some(value) = &self.direct_io {
            record.text(&format!(
                "File I/O direct_io: {} (from {})",
                value.value, value.source
            ));
        }
    }

    fn log_network(&self, record: &mut impl Record) {
        let mut line = b"TLS trust: ".to_vec();
        match &self.trust.value {
            Trust::Platform => line.extend_from_slice(b"platform store"),
            Trust::Embedded => {
                line.extend_from_slice(format!("embedded {CACERT_ENTRY_NAME}").as_bytes());
            }
            Trust::File(path) => line.extend_from_slice(path.as_os_str().as_encoded_bytes()),
        }
        line.extend_from_slice(format!(" (from {})", self.trust.source).as_bytes());
        record(&line);
        let keep_alive = if self.keep_alive.value {
            "enabled"
        } else {
            "disabled"
        };
        record.text(&format!(
            "TCP keepalive: {keep_alive} (from {})",
            self.keep_alive.source
        ));
        record.text(&format!(
            "Connect timeout: {} ms (from {})",
            self.connect_timeout_ms.value, self.connect_timeout_ms.source
        ));
        let signing = if self.signing.value {
            "signed"
        } else {
            "anonymous"
        };
        record.text(&format!(
            "Request signing: {signing} (from {})",
            self.signing.source
        ));
        let retry = match self.retry_mode.value {
            RetryMode::Standard => "standard",
            RetryMode::Adaptive => "adaptive",
        };
        record.text(&format!(
            "Retry mode: {retry} (from {})",
            self.retry_mode.source
        ));
        let attempts = self
            .retry_attempts
            .value
            .map_or_else(|| "CRT default".into(), |value| value.to_string());
        record.text(&format!(
            "Max attempts: {attempts} (from {})",
            self.retry_attempts.source
        ));
    }

    fn log_endpoint(&self, record: &mut impl Record) {
        let style = match self.addressing_style.value {
            AddressingStyle::Auto => "auto",
            AddressingStyle::Virtual => "virtual",
            AddressingStyle::Path => "path",
        };
        record.text(&format!(
            "S3 addressing style: {style} (from {})",
            self.addressing_style.source
        ));
        record.text(&format!(
            "S3 accelerate endpoint: {} (from {})",
            self.use_accelerate_endpoint.value, self.use_accelerate_endpoint.source
        ));
        record.text(&format!(
            "S3 block dual-stack endpoint: {} (from {})",
            self.use_dualstack_endpoint.value, self.use_dualstack_endpoint.source
        ));
    }
}

#[cfg(test)]
mod tests;
