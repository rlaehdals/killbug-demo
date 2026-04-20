package com.killbug.webhook.config;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class SlackProperties {
    private String apiUrl;
    private String bugChannelId;
    private String botToken;
    private String signingSecret;
}
