package com.sigma.scm.controller;

import com.sigma.scm.domain.ImportBatch;
import com.sigma.scm.repository.ImportBatchRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class BatchControllerTest {

    @Mock
    private ImportBatchRepository importBatchRepository;

    @InjectMocks
    private BatchController batchController;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testGetBatches() {
        List<ImportBatch> mockBatches = new ArrayList<>();
        ImportBatch batch = new ImportBatch();
        batch.setStatus("APPROVED");
        mockBatches.add(batch);

        when(importBatchRepository.findByStatus("APPROVED")).thenReturn(mockBatches);

        ResponseEntity<List<ImportBatch>> response = batchController.getBatches("APPROVED");

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(1, response.getBody().size());
        assertEquals("APPROVED", response.getBody().get(0).getStatus());
    }
}
