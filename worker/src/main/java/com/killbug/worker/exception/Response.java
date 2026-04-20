package com.killbug.worker.exception;

import java.time.ZoneOffset;
import java.time.ZonedDateTime;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import com.killbug.worker.util.ApiResponse;

import lombok.Getter;
import lombok.ToString;

@Getter
@ToString
public enum Response {

    OK(HttpStatus.OK, SpecificStatus.OK);

    private final HttpStatus httpStatus;
    private final SpecificStatus specificStatus;

    Response(final HttpStatus httpStatus, final SpecificStatus specificStatus) {
        this.httpStatus = httpStatus;
        this.specificStatus = specificStatus;
    }

    public ResponseEntity getApiResponse(Object o) {
        return ResponseEntity
                .status(this.httpStatus)
                .body(ApiResponse.builder()
                        .message(this.specificStatus.name())
                        .sendTime(ZonedDateTime.now(ZoneOffset.UTC))
                        .data(o)
                        .build()
                );
    }
}
