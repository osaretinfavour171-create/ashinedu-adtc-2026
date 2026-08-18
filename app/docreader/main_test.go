package main

import (
	"os"
	"path/filepath"
	"testing"
)

func loadTestServer(t *testing.T) *Server {
	t.Helper()
	// data dir is ../../data relative to this test file
	dataDir := filepath.Join("..", "..", "data")
	if _, err := os.Stat(filepath.Join(dataDir, "interactions.json")); err != nil {
		t.Skipf("data not found at %s (run tests from app/docreader)", dataDir)
	}
	interactions, err := loadInteractions(filepath.Join(dataDir, "interactions.json"))
	if err != nil {
		t.Fatalf("load interactions: %v", err)
	}
	conditions, err := loadConditions(filepath.Join(dataDir, "stg_conditions"))
	if err != nil {
		t.Fatalf("load conditions: %v", err)
	}
	s := &Server{interactions: interactions, conditions: conditions}
	s.buildIndexes()
	return s
}

func TestLoadsData(t *testing.T) {
	s := loadTestServer(t)
	if len(s.interactions) < 100 {
		t.Errorf("expected >=100 interactions, got %d", len(s.interactions))
	}
	if len(s.conditions) < 200 {
		t.Errorf("expected >=200 conditions, got %d", len(s.conditions))
	}
}

func TestSearchConditionsAsthma(t *testing.T) {
	s := loadTestServer(t)
	res := s.searchConditions("bronchial asthma treatment", 5)
	if len(res) == 0 {
		t.Fatal("no conditions found")
	}
	if res[0].Name != "Bronchial Asthma" {
		t.Errorf("expected Bronchial Asthma first, got %s", res[0].Name)
	}
}

func TestSearchConditionsFever(t *testing.T) {
	s := loadTestServer(t)
	res := s.searchConditions("the child has fever and vomiting", 5)
	if len(res) == 0 {
		t.Fatal("no conditions found")
	}
	names := map[string]bool{}
	for _, c := range res {
		names[c.Name] = true
	}
	if !names["Fevers"] {
		t.Errorf("expected Fevers in results, got %v", res)
	}
}

func TestSearchDrugMetronidazoleWarfarin(t *testing.T) {
	s := loadTestServer(t)
	drug, its := s.searchDrug("metronidazole and warfarin")
	if drug != "Metronidazole" {
		t.Errorf("expected Metronidazole, got %q", drug)
	}
	found := false
	for _, it := range its {
		if it.DrugB == "Warfarin" {
			found = true
		}
	}
	if !found {
		t.Error("expected a Metronidazole-Warfarin interaction")
	}
}

func TestSearchDrugArtemetherQuinine(t *testing.T) {
	s := loadTestServer(t)
	drug, its := s.searchDrug("artemether lumefantrine and quinine")
	if drug != "Artemether/Lumefantrine" {
		t.Errorf("expected Artemether/Lumefantrine, got %q", drug)
	}
	// The quinine interaction must be ranked first (partner word in query).
	if len(its) == 0 || its[0].DrugB != "Quinine" {
		t.Errorf("expected Quinine interaction first, got %v", its)
	}
}

func TestStem(t *testing.T) {
	if stem("Artemether/Lumefantrine") != "artemether lumefantrine" {
		t.Errorf("stem failed: %q", stem("Artemether/Lumefantrine"))
	}
	if stem("  MixEd   CASE  ") != "mixed case" {
		t.Errorf("stem failed: %q", stem("  MixEd   CASE  "))
	}
}
