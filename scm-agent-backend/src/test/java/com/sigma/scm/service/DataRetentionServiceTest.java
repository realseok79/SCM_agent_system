package com.sigma.scm.service;

import com.sigma.scm.repository.BatchStatusHistoryRepository;
import com.sigma.scm.repository.ExcelParseLogRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class DataRetentionServiceTest {

    @Mock
    private BatchStatusHistoryRepository batchStatusHistoryRepository;

    @Mock
    private ExcelParseLogRepository excelParseLogRepository;

    @InjectMocks
    private DataRetentionService dataRetentionService;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testRunRetentionPolicySuccess() {
        when(batchStatusHistoryRepository.deleteOlderThan(any(LocalDateTime.class))).thenReturn(5);
        when(excelParseLogRepository.deleteOlderThan(any(LocalDateTime.class))).thenReturn(10);

        assertDoesNotThrow(() -> dataRetentionService.runRetentionPolicy(90));

        verify(batchStatusHistoryRepository, times(1)).deleteOlderThan(any(LocalDateTime.class));
        verify(excelParseLogRepository, times(1)).deleteOlderThan(any(LocalDateTime.class));
    }

    @Test
    public void testRunRetentionPolicyErrorPropagation() {
        when(batchStatusHistoryRepository.deleteOlderThan(any(LocalDateTime.class)))
                .thenThrow(new RuntimeException("DB Connection Timeout"));

        assertThrows(RuntimeException.class, () -> dataRetentionService.runRetentionPolicy(90));
    }
}
