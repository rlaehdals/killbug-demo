package com.killbug.worker.exception;

import lombok.Getter;

@Getter
public class ResponseException extends RuntimeException {

    private final Response responseCode;

    public ResponseException(Response responseCode) {
        super(responseCode.getSpecificStatus().toString());
        this.responseCode = responseCode;
    }
}
