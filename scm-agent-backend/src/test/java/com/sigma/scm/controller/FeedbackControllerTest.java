package com.sigma.scm.controller;

import com.sigma.scm.service.FeedbackService;
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

public class FeedbackControllerTest {

    @Mock
    private FeedbackService feedbackService;

    @InjectMocks
    private FeedbackController feedbackController;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testRejectMapping() {
        FeedbackController.RejectionRequest request = new FeedbackController.RejectionRequest();
        request.setCompanyId("COMPANY_SIGMA");
        request.setRawHeader("물품수량");
        request.setMappedColumn("quantity");

        ResponseEntity<Map<String, String>> response = feedbackController.rejectMapping(request);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals("SUCCESS", response.getBody().get("status"));
        verify(feedbackService, times(1)).processMappingRejection("COMPANY_SIGMA", "물품수량", "quantity");
    }
}
