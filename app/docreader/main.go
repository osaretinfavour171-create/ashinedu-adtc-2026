// DocReader: local HTTP server for PidginPharma.
//
// Serves:
//
//	GET  /health           -> {"ok": true, "conditions": N, "interactions": M}
//	POST /search           -> {query: "..."}  -> conditions + interactions matches
//	GET  /interactions     -> full interaction list
//
// All data is loaded from local JSON files at startup. Zero network access.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

type Interaction struct {
	DrugA          string `json:"drug_a"`
	DrugB          string `json:"drug_b"`
	Severity       string `json:"severity"`
	Mechanism      string `json:"mechanism"`
	Source         string `json:"source"`
	Recommendation string `json:"recommendation"`
}

type Condition struct {
	Name          string                 `json:"condition_name"`
	Slug          string                 `json:"condition_slug"`
	Source        string                 `json:"source"`
	Introduction  string                 `json:"introduction"`
	Features      []string               `json:"clinical_features"`
	Treatment     map[string]interface{} `json:"treatment"`
	Complications []string               `json:"complications"`
	Prevention    []string               `json:"prevention"`
	Raw           map[string]interface{} `json:"-"`
}

// Server state --------------------------------------------------------------
type Server struct {
	interactions []Interaction
	conditions   []Condition
	condBySlug   map[string]Condition
	// stemmed search index: word -> list of condition indices
	condIndex map[string][]int
	// name index: word -> condition indices where the word is IN the name
	nameIndex map[string][]int
	// normalized drug name -> list of interaction indices
	drugIndex map[string][]int
}

// ---------------------------------------------------------------------------
// Loading
// ---------------------------------------------------------------------------

func loadInteractions(path string) ([]Interaction, error) {
	info, err := os.Stat(path)
	if err != nil {
		return nil, err
	}
	// SECURITY: reject files over 10 MB (interaction matrix is ~200 KB).
	const maxInteractionSize = 10 << 20
	if info.Size() > maxInteractionSize {
		return nil, fmt.Errorf("interactions.json too large: %d bytes (max %d)", info.Size(), maxInteractionSize)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var wrapper struct {
		Interactions []Interaction `json:"interactions"`
	}
	if err := json.Unmarshal(data, &wrapper); err != nil {
		return nil, err
	}
	return wrapper.Interactions, nil
}

func loadConditions(dir string) ([]Condition, error) {
	const maxConditionSize = 512 << 10 // 512 KB per condition file
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	var conds []Condition
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".json") {
			continue
		}
		path := filepath.Join(dir, e.Name())
		info, statErr := os.Stat(path)
		if statErr != nil || info.Size() > maxConditionSize {
			continue
		}
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		var raw map[string]interface{}
		if err := json.Unmarshal(data, &raw); err != nil {
			log.Printf("skip bad condition %s: %v", e.Name(), err)
			continue
		}
		c := Condition{Raw: raw}
		c.Name, _ = raw["condition_name"].(string)
		c.Slug, _ = raw["condition_slug"].(string)
		c.Source, _ = raw["source"].(string)
		c.Introduction, _ = raw["introduction"].(string)
		c.Features = toStringSlice(raw["clinical_features"])
		c.Complications = toStringSlice(raw["complications"])
		c.Prevention = toStringSlice(raw["prevention"])
		if tr, ok := raw["treatment"].(map[string]interface{}); ok {
			c.Treatment = tr
		}
		if c.Name == "" {
			c.Name = strings.TrimSuffix(e.Name(), ".json")
		}
		conds = append(conds, c)
	}
	sort.Slice(conds, func(i, j int) bool { return conds[i].Name < conds[j].Name })
	return conds, nil
}

func toStringSlice(v interface{}) []string {
	switch t := v.(type) {
	case []interface{}:
		out := make([]string, 0, len(t))
		for _, x := range t {
			if s, ok := x.(string); ok {
				out = append(out, s)
			}
		}
		return out
	case []string:
		return t
	default:
		return nil
	}
}

// ---------------------------------------------------------------------------
// Indexing
// ---------------------------------------------------------------------------

// stem performs a very light normalization: lowercase, strip non-alphanumerics,
// collapse whitespace.
func stem(s string) string {
	s = strings.ToLower(s)
	var b strings.Builder
	space := false
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			if space && b.Len() > 0 {
				b.WriteRune(' ')
			}
			space = false
			b.WriteRune(r)
		} else {
			space = true
		}
	}
	return b.String()
}

func words(s string) []string {
	return strings.Fields(stem(s))
}

func (s *Server) buildIndexes() {
	s.condIndex = map[string][]int{}
	s.nameIndex = map[string][]int{}
	for i, c := range s.conditions {
		seen := map[string]bool{}
		// Name words go into their own index (weighted higher in scoring).
		for _, w := range words(c.Name) {
			if len(w) < 2 || seen[w] {
				continue
			}
			seen[w] = true
			s.nameIndex[w] = append(s.nameIndex[w], i)
		}
		seen = map[string]bool{}
		for _, w := range words(c.Name + " " + c.Introduction + " " + strings.Join(c.Features, " ")) {
			if len(w) < 2 || seen[w] {
				continue
			}
			seen[w] = true
			s.condIndex[w] = append(s.condIndex[w], i)
		}
	}
	s.drugIndex = map[string][]int{}
	for i, it := range s.interactions {
		for _, d := range []string{it.DrugA, it.DrugB} {
			for _, w := range words(d) {
				if len(w) < 2 {
					continue
				}
				s.drugIndex[w] = append(s.drugIndex[w], i)
			}
		}
	}
}

var stopWords = map[string]bool{
	"the": true, "a": true, "an": true, "and": true, "or": true, "of": true,
	"in": true, "on": true, "for": true, "with": true, "is": true, "are": true,
	"was": true, "were": true, "has": true, "have": true, "had": true, "be": true,
	"to": true, "from": true, "at": true, "by": true, "it": true, "its": true,
	"this": true, "that": true, "these": true, "those": true, "my": true, "me": true,
	"we": true, "our": true, "you": true, "your": true, "he": true, "she": true,
	"him": true, "her": true, "they": true, "them": true, "what": true, "how": true,
	"can": true, "could": true, "will": true, "would": true, "should": true,
	"do": true, "does": true, "did": true, "i": true, "am": true, "about": true,
	"than": true, "then": true, "there": true, "here": true, "when": true,
	"where": true, "which": true, "who": true, "whom": true, "if": true,
	"please": true, "help": true, "need": true, "want": true, "get": true,
	"got": true, "patient": true,
}

// ageWords signal the patient is a child; pregnancyWords mark conditions
// that apply to pregnant adults. When a query mentions a child, conditions
// tied to pregnancy/obstetrics are demoted so a child with fever+vomiting
// is not matched to morning sickness.
var ageWords = map[string]bool{
	"child": true, "children": true, "baby": true, "babies": true,
	"pikin": true, "infant": true, "infants": true, "neonate": true,
	"neonatal": true, "newborn": true, "toddler": true, "kid": true,
}

var pregnancyPatterns = []string{
	"gravidarum", "pregnancy", "pregnant", "antenatal", "postnatal",
	"obstetric", "labour", "labor", "puerper", "eclampsia", "miscarriage",
	"abortion", "gestational", "amniotic", "placenta", "prenatal",
	"maternal", "chorio", "nuchal", "caesarean", "cesarean", "birth canal",
}

func mentionsChild(query string) bool {
	for _, w := range words(query) {
		if ageWords[w] {
			return true
		}
	}
	return false
}

func isPregnancyCondition(name string) bool {
	low := strings.ToLower(name)
	for _, p := range pregnancyPatterns {
		if strings.Contains(low, p) {
			return true
		}
	}
	return false
}

// termFreq counts how many times each meaningful query word appears in the
// condition index, so we can weight rarer (more specific) words higher.
func (s *Server) termFreq(w string) int {
	return len(s.condIndex[w])
}

func (s *Server) searchConditions(query string, limit int) []Condition {
	if limit <= 0 {
		limit = 5
	}
	qWords := words(query)
	if len(qWords) == 0 {
		return nil
	}
	// Keep only meaningful words (drop stopwords). Age words are kept
	// out of the score (they are common in condition names and would
	// dominate) but are still detected for the pregnancy demotion below.
	var meaningful []string
	for _, w := range qWords {
		if !stopWords[w] && !ageWords[w] {
			meaningful = append(meaningful, w)
		}
	}
	if len(meaningful) == 0 {
		meaningful = qWords
	}
	// Score with inverse-frequency weighting: rarer words count more.
	type scored struct {
		idx int
		hit float64
	}
	scoreMap := map[int]float64{}
	hitsMap := map[int]int{}
	for _, qw := range meaningful {
		weight := 1.0
		freq := s.termFreq(qw)
		if freq > 0 {
			// words appearing in fewer conditions weigh more
			weight = 1.0 + 8.0/float64(freq)
		}
		for _, idx := range s.condIndex[qw] {
			scoreMap[idx] += weight
			hitsMap[idx]++
		}
		// words found in the condition NAME get a big bonus
		for _, idx := range s.nameIndex[qw] {
			scoreMap[idx] += weight * 3.0
			hitsMap[idx]++
		}
	}
	// Age-aware demotion: a child query should not surface pregnancy
	// conditions (e.g. Hyperemesis Gravidarum) ahead of paediatric ones.
	childQ := mentionsChild(query)
	for idx := range scoreMap {
		if childQ && isPregnancyCondition(s.conditions[idx].Name) {
			scoreMap[idx] *= 0.15
		}
	}
	var scoredList []scored
	for idx, n := range scoreMap {
		scoredList = append(scoredList, scored{idx, n})
	}
	sort.Slice(scoredList, func(i, j int) bool {
		if scoredList[i].hit != scoredList[j].hit {
			return scoredList[i].hit > scoredList[j].hit
		}
		if hitsMap[scoredList[i].idx] != hitsMap[scoredList[j].idx] {
			return hitsMap[scoredList[i].idx] > hitsMap[scoredList[j].idx]
		}
		return s.conditions[scoredList[i].idx].Name < s.conditions[scoredList[j].idx].Name
	})
	out := make([]Condition, 0, limit)
	for i, sc := range scoredList {
		if i >= limit {
			break
		}
		out = append(out, s.conditions[sc.idx])
	}
	return out
}

func (s *Server) searchDrug(query string) (string, []Interaction) {
	qWords := words(query)
	if len(qWords) == 0 {
		return "", nil
	}
	// Find best drug name match: drug whose name shares the most query words.
	type scored struct {
		name  string
		hit   int
		first int // index of first matching word in the query (tie-break)
		index int
	}
	best := map[string]scored{}
	for i, it := range s.interactions {
		for _, d := range []string{it.DrugA, it.DrugB} {
			dw := words(d)
			hit := 0
			first := 1 << 30
			for qi, qw := range qWords {
				for _, w := range dw {
					if qw == w {
						hit++
						if qi < first {
							first = qi
						}
					}
				}
			}
			if hit == 0 {
				continue
			}
			if cur, ok := best[d]; !ok || hit > cur.hit {
				best[d] = scored{d, hit, first, i}
			}
		}
	}
	if len(best) == 0 {
		return "", nil
	}
	var top scored
	top.first = 1 << 30
	for _, sc := range best {
		if sc.hit > top.hit || (sc.hit == top.hit && sc.first < top.first) {
			top = sc
		}
	}
	var out []Interaction
	seen := map[string]bool{}
	partnerWords := map[string]bool{}
	for _, w := range qWords {
		partnerWords[w] = true
	}
	for _, it := range s.interactions {
		if it.DrugA == top.name || it.DrugB == top.name {
			key := it.DrugA + "|" + it.DrugB
			if !seen[key] {
				seen[key] = true
				out = append(out, it)
			}
		}
	}
	// Interactions whose partner drug is also mentioned in the query rank first.
	sort.SliceStable(out, func(i, j int) bool {
		return partnerScore(out[i], top.name, partnerWords) > partnerScore(out[j], top.name, partnerWords)
	})
	return top.name, out
}

// partnerScore counts how many query words appear in the partner drug name.
func partnerScore(it Interaction, mainDrug string, qWords map[string]bool) int {
	partner := it.DrugB
	if it.DrugB == mainDrug {
		partner = it.DrugA
	}
	score := 0
	for _, w := range words(partner) {
		if qWords[w] {
			score++
		}
	}
	return score
}

// ---------------------------------------------------------------------------
// HTTP handlers
// ---------------------------------------------------------------------------

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]interface{}{
		"ok":           true,
		"conditions":   len(s.conditions),
		"interactions": len(s.interactions),
		"service":      "PidginPharma DocReader",
	})
}

func (s *Server) handleSearch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	// Require JSON Content-Type to prevent form-encoded abuse.
	if ct := r.Header.Get("Content-Type"); ct != "" &&
		!strings.Contains(ct, "application/json") {
		http.Error(w, "content-type must be application/json", http.StatusBadRequest)
		return
	}
	// Limit request body to 8 KB: queries are short clinical questions.
	r.Body = http.MaxBytesReader(w, r.Body, 8192)
	var req struct {
		Query string `json:"query"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "bad json", http.StatusBadRequest)
		return
	}
	query := strings.TrimSpace(req.Query)
	if query == "" {
		http.Error(w, "empty query", http.StatusBadRequest)
		return
	}

	resp := map[string]interface{}{
		"query":        query,
		"conditions":   s.searchConditions(query, 5),
		"drug_match":   nil,
		"interactions": []Interaction{},
	}
	if drug, its := s.searchDrug(query); drug != "" {
		resp["drug_match"] = drug
		resp["interactions"] = its
	}
	writeJSON(w, resp)
}

func (s *Server) handleInteractions(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]interface{}{"interactions": s.interactions})
}

func writeJSON(w http.ResponseWriter, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(v)
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

func main() {
	addr := flag.String("addr", "127.0.0.1:8765", "listen address")
	dataDir := flag.String("data", "", "path to app/data directory")
	flag.Parse()

	if *dataDir == "" {
		// default: look relative to this binary
		exe, err := os.Executable()
		if err == nil {
			*dataDir = filepath.Join(filepath.Dir(exe), "..", "data")
		}
	}
	interPath := filepath.Join(*dataDir, "interactions.json")
	condDir := filepath.Join(*dataDir, "stg_conditions")

	interactions, err := loadInteractions(interPath)
	if err != nil {
		log.Fatalf("load interactions: %v", err)
	}
	conditions, err := loadConditions(condDir)
	if err != nil {
		log.Fatalf("load conditions: %v", err)
	}

	srv := &Server{
		interactions: interactions,
		conditions:   conditions,
	}
	srv.buildIndexes()

	mux := http.NewServeMux()
	mux.HandleFunc("/health", srv.handleHealth)
	mux.HandleFunc("/search", srv.handleSearch)
	mux.HandleFunc("/interactions", srv.handleInteractions)

	// SECURITY: warn if binding to a non-localhost address.
	if !strings.HasPrefix(*addr, "127.") && !strings.HasPrefix(*addr, "localhost") {
		log.Printf("WARNING: binding to %s exposes DocReader to the network. "+
			"Use 127.0.0.1:8765 for localhost-only access.", *addr)
	}

	log.Printf("PidginPharma DocReader ready on %s (conditions=%d, interactions=%d)",
		*addr, len(conditions), len(interactions))

	httpServer := &http.Server{
		Addr:              *addr,
		Handler:           mux,
		ReadHeaderTimeout: 10 * time.Second,
	}
	if err := httpServer.ListenAndServe(); err != nil {
		log.Fatalf("server: %v", err)
	}
}

// keep fmt import used even if future edits trim features
var _ = fmt.Sprintf
