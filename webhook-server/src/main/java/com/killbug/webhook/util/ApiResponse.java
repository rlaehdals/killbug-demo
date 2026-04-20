package com.killbug.webhook.util;

import java.io.Serializable;
import java.time.ZonedDateTime;

import lombok.Builder;
import lombok.Getter;
import lombok.ToString;

@Getter
@ToString
public class ApiResponse<T> implements Serializable {

    private static final long serialVersionUID = -29184281L;

    private final T data;

    private final String message;

    private final ZonedDateTime sendTime;

    @Builder
    private ApiResponse(T data, String message, ZonedDateTime sendTime) {
        this.data = data;
        this.message = message;
        this.sendTime = sendTime;
    }
}
