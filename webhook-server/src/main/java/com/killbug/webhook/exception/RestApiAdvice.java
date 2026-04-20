package com.killbug.webhook.exception;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.killbug.webhook.util.ApiResponse;

@RestControllerAdvice
public class RestApiAdvice {

    @ExceptionHandler(ResponseException.class)
    public ResponseEntity<ApiResponse> runtimeExceptionHandler(ResponseException e) {
        return e.getResponseCode().getApiResponse(null);
    }
}
