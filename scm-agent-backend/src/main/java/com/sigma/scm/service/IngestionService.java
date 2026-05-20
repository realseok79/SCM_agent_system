package com.sigma.scm.service;

import com.sigma.scm.domain.ImportBatch;
import com.sigma.scm.repository.ImportBatchRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.HexFormat;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Transactional
public class IngestionService {

    private final ImportBatchRepository importBatchRepository;

    public ImportBatch startIngestion(String companyId, MultipartFile file) throws IOException {
        String batchId = "BATCH-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        
        byte[] fileBytes = file.getBytes();
        String fileSha256 = calculateSha256(fileBytes);

        ImportBatch batch = new ImportBatch();
        batch.setBatchId(batchId);
        batch.setCompanyId(companyId);
        batch.setFileName(file.getOriginalFilename());
        batch.setFileSha256(fileSha256);
        batch.setStatus("CREATED"); // 초기 상태 머신 상태
        batch.setVersion(1);
        batch.setCreatedAt(LocalDateTime.now());
        batch.setUpdatedAt(LocalDateTime.now());

        return importBatchRepository.save(batch);
    }

    private String calculateSha256(byte[] bytes) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(bytes);
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }
}
