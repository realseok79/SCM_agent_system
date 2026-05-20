package com.sigma.scm.controller;

import com.sigma.scm.domain.CompanyExcelMapping;
import com.sigma.scm.service.FeedbackService;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/feedback")
@RequiredArgsConstructor
public class FeedbackController {

    private final FeedbackService feedbackService;

    @PostMapping("/reject-mapping")
    public ResponseEntity<Map<String, String>> rejectMapping(@RequestBody RejectionRequest request) {
        feedbackService.processMappingRejection(
                request.getCompanyId(),
                request.getRawHeader(),
                request.getMappedColumn()
        );
        return ResponseEntity.ok(Map.of("status", "SUCCESS", "message", "Feedback processed successfully."));
    }

    @GetMapping("/history/{companyId}")
    public ResponseEntity<List<MappingScoreDTO>> getFeedbackHistory(@PathVariable("companyId") String companyId) {
        List<CompanyExcelMapping> history = feedbackService.getMappingHistory(companyId);
        List<MappingScoreDTO> dtos = history.stream().map(m -> {
            double rawConf = m.getConfidence() != null ? m.getConfidence() : 0.5;
            double negScore = m.getNegativeScore() != null ? m.getNegativeScore() : 0.0;
            // 실효 신뢰도 계산: 패널티 계수 0.15 적용 후 0.0~1.0 사이로 클리핑
            double effectiveConf = Math.max(0.0, Math.min(1.0, rawConf - (negScore * 0.15)));
            
            return new MappingScoreDTO(
                    m.getId().getRawHeader(),
                    m.getId().getMappedColumn(),
                    rawConf,
                    negScore,
                    effectiveConf,
                    m.getUpdatedAt()
            );
        }).collect(Collectors.toList());
        
        return ResponseEntity.ok(dtos);
    }

    @Data
    public static class RejectionRequest {
        private String companyId;
        private String rawHeader;
        private String mappedColumn;
    }

    @Data
    @AllArgsConstructor
    public static class MappingScoreDTO {
        private String rawHeader;
        private String mappedColumn;
        private Double confidence;
        private Double negativeScore;
        private Double effectiveConfidence;
        private LocalDateTime updatedAt;
    }
}
