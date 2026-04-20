package com.killbug.worker.config;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class SlackProperties {
    private String apiUrl;
    private String botToken;
}
