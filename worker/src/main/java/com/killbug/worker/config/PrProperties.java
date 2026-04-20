package com.killbug.worker.config;

import java.util.ArrayList;
import java.util.List;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class PrProperties {
    private boolean draft;
    private List<String> labels = new ArrayList<>();
}
