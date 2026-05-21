package com.sigma.scm.controller;

import com.sigma.scm.domain.ImportBatch;
import com.sigma.scm.repository.ImportBatchRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/ingestion")
@RequiredArgsConstructor
public class BatchController {

    private final ImportBatchRepository importBatchRepository;

    @GetMapping("/batches")
    public ResponseEntity<List<ImportBatch>> getBatches(@RequestParam("status") String status) {
        return ResponseEntity.ok(importBatchRepository.findByStatus(status));
    }
}
