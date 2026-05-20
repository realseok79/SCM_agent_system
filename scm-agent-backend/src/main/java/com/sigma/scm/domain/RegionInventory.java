package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "region_inventory")
@Data
@NoArgsConstructor
public class RegionInventory {

    @EmbeddedId
    private RegionInventoryId id;

    @Column(nullable = false)
    private Double quantity;

    @Column(name = "source_batch_id", nullable = false, length = 100)
    private String sourceBatchId = "SEED_DATA";

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();
}
