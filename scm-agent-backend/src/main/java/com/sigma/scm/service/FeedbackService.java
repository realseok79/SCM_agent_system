package com.sigma.scm.service;

import com.sigma.scm.domain.CompanyExcelMapping;
import com.sigma.scm.domain.CompanyExcelMappingId;
import com.sigma.scm.repository.CompanyExcelMappingRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional
public class FeedbackService {

    private final CompanyExcelMappingRepository mappingRepository;

    public void processMappingRejection(String companyId, String rawHeader, String mappedColumn) {
        // 1. Decay all negative scores for this company: S_t = 0.9 * S_{t-1}
        List<CompanyExcelMapping> mappings = mappingRepository.findByIdCompanyId(companyId);
        for (CompanyExcelMapping mapping : mappings) {
            mapping.setNegativeScore(mapping.getNegativeScore() * 0.9);
            mapping.setUpdatedAt(LocalDateTime.now());
        }

        // 2. Add R_t = 1.0 to the target mapping
        CompanyExcelMappingId targetId = new CompanyExcelMappingId(companyId, rawHeader, mappedColumn);
        CompanyExcelMapping targetMapping = mappingRepository.findById(targetId)
                .orElseGet(() -> {
                    CompanyExcelMapping m = new CompanyExcelMapping();
                    m.setId(targetId);
                    m.setConfidence(0.5); // Default confidence
                    m.setNegativeScore(0.0);
                    return m;
                });

        targetMapping.setNegativeScore(targetMapping.getNegativeScore() + 1.0);
        targetMapping.setUpdatedAt(LocalDateTime.now());
        mappingRepository.save(targetMapping);
    }

    @Transactional(readOnly = true)
    public List<CompanyExcelMapping> getMappingHistory(String companyId) {
        return mappingRepository.findByIdCompanyId(companyId);
    }
}
