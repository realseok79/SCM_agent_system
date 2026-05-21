package com.sigma.scm.controller;

import com.sigma.scm.saeie.IngestionPipelineService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/regions")
@RequiredArgsConstructor
public class IngestionController {

    private final IngestionPipelineService ingestionPipelineService;

    @PostMapping("/upload")
    public ResponseEntity<Map<String, Object>> uploadSpreadsheet(
            @RequestParam("company_id") String companyId,
            @RequestParam("file") MultipartFile file) {
        
        try {
            Map<String, Object> result = ingestionPipelineService.ingestSpreadsheet(companyId, file, "SYSTEM");
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }

    @PostMapping("/upload/confirm")
    public ResponseEntity<Map<String, Object>> confirmSpreadsheet(
            @RequestParam("batch_id") String batchId,
            @RequestBody(required = false) Map<String, String> userOverrides) {
        
        try {
            Map<String, Object> result = ingestionPipelineService.confirmSpreadsheet(batchId, userOverrides, "SYSTEM");
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }
}

