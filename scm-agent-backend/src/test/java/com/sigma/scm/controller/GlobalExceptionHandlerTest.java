package com.sigma.scm.controller;

import com.sigma.scm.service.SlackAlertService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class GlobalExceptionHandlerTest {

    @Mock
    private SlackAlertService slackAlertService;

    @InjectMocks
    private GlobalExceptionHandler globalExceptionHandler;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testHandleAllExceptions() {
        Exception testEx = new RuntimeException("Simulated Database Timeout Exception");

        ResponseEntity<Map<String, Object>> response = globalExceptionHandler.handleAllExceptions(testEx);

        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("Internal Server Error", response.getBody().get("error"));
        assertEquals("An unexpected error occurred. Please contact the administrator.", response.getBody().get("message"));

        verify(slackAlertService, times(1)).sendSlackAlert(
                eq("Unhandled Exception Occurred in Backend"),
                contains("Simulated Database Timeout Exception"),
                eq("ERROR")
        );
    }
}
