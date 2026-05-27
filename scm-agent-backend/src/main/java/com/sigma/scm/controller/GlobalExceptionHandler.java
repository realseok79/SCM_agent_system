package com.sigma.scm.controller;

import com.sigma.scm.service.SlackAlertService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.HashMap;
import java.util.Map;

@RestControllerAdvice
@RequiredArgsConstructor
@Slf4j
public class GlobalExceptionHandler {

    private final SlackAlertService slackAlertService;

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleAllExceptions(Exception ex) {
        log.error("[GLOBAL-EXCEPTION] Intercepted unhandled exception: {}", ex.getMessage(), ex);

        // 1. Send Slack Alert
        String severity = "ERROR";
        if (ex instanceof NullPointerException || ex instanceof IllegalArgumentException) {
            severity = "WARNING";
        }
        slackAlertService.sendSlackAlert(
                "Unhandled Exception Occurred in Backend",
                ex.getClass().getName() + ": " + ex.getMessage(),
                severity
        );

        // 2. Return Response
        Map<String, Object> body = new HashMap<>();
        body.put("status", HttpStatus.INTERNAL_SERVER_ERROR.value());
        body.put("error", "Internal Server Error");
        body.put("message", "An unexpected error occurred. Please contact the administrator.");
        return new ResponseEntity<>(body, HttpStatus.INTERNAL_SERVER_ERROR);
    }
}
