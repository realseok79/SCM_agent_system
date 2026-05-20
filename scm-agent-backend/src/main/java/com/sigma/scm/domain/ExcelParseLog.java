package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "excel_parse_logs")
@Data
@NoArgsConstructor
public class ExcelParseLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "import_batch_id", length = 100)
    private String importBatchId;

    @Column(name = "company_id", nullable = false, length = 100)
    private String companyId;

    @Column(nullable = false, length = 50)
    private String severity;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String message;

    @Column(name = "column_name", length = 100)
    private String columnName;

    @Column(name = "row_index")
    private Integer rowIndex;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}
