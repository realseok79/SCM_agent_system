package com.sigma.scm.repository;

import com.sigma.scm.domain.BatchStatusHistory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface BatchStatusHistoryRepository extends JpaRepository<BatchStatusHistory, Long> {
    List<BatchStatusHistory> findByBatchId(String batchId);
}
