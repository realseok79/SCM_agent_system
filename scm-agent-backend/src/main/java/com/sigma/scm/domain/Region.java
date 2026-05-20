package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.ToString;

import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.Set;

@Entity
@Table(name = "regions")
@Data
@NoArgsConstructor
@ToString(exclude = "users")
public class Region {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "region_name", nullable = false, unique = true, length = 100)
    private String regionName;

    @Column(name = "region_code", nullable = false, unique = true, length = 50)
    private String regionCode;

    @Column(length = 255)
    private String description;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    @ManyToMany(mappedBy = "regions", fetch = FetchType.LAZY)
    private Set<User> users = new HashSet<>();
}
