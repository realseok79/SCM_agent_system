package com.sigma.scm.service;

import com.sigma.scm.domain.CompanyExcelMapping;
import com.sigma.scm.domain.CompanyExcelMappingId;
import com.sigma.scm.repository.CompanyExcelMappingRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class FeedbackServiceTest {

    @Mock
    private CompanyExcelMappingRepository mappingRepository;

    @InjectMocks
    private FeedbackService feedbackService;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testProcessMappingRejectionDecayAndIncrement() {
        String companyId = "COMPANY_SIGMA";
        String rawHeader = "물품수량";
        String mappedColumn = "quantity";

        // Setup existing mappings for decay verification
        List<CompanyExcelMapping> existingMappings = new ArrayList<>();
        CompanyExcelMapping existing1 = new CompanyExcelMapping();
        existing1.setId(new CompanyExcelMappingId(companyId, "날짜", "date"));
        existing1.setNegativeScore(2.0);
        existingMappings.add(existing1);

        CompanyExcelMapping existing2 = new CompanyExcelMapping();
        CompanyExcelMappingId targetId = new CompanyExcelMappingId(companyId, rawHeader, mappedColumn);
        existing2.setId(targetId);
        existing2.setNegativeScore(1.0);
        existingMappings.add(existing2);

        when(mappingRepository.findByIdCompanyId(companyId)).thenReturn(existingMappings);
        when(mappingRepository.findById(targetId)).thenReturn(Optional.of(existing2));

        feedbackService.processMappingRejection(companyId, rawHeader, mappedColumn);

        // Verify decay: existing1: 2.0 * 0.9 = 1.8
        assertEquals(1.8, existing1.getNegativeScore(), 0.0001);
        // Verify increment on target mapping: (1.0 * 0.9) + 1.0 = 1.9
        assertEquals(1.9, existing2.getNegativeScore(), 0.0001);

        verify(mappingRepository, times(1)).save(existing2);
    }
}
