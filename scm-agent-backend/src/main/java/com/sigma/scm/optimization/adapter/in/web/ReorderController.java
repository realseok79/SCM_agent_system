package com.sigma.scm.optimization.adapter.in.web;

import com.sigma.scm.optimization.application.port.in.ReorderProcessUseCase;
import com.sigma.scm.optimization.domain.model.ReorderDecision;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/optimization")
@RequiredArgsConstructor
public class ReorderController {

    private final ReorderProcessUseCase reorderProcessUseCase;

    @PostMapping("/reorder-check")
    public ResponseEntity<ReorderDecision> checkReorder(
            @RequestParam String productName,
            @RequestParam String regionCode
    ) {
        ReorderDecision decision = reorderProcessUseCase.evaluateReorder(productName, regionCode);
        return ResponseEntity.ok(decision);
    }
}
