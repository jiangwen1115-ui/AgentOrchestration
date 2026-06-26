package oabp

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestClientCoreEndpoints(t *testing.T) {
	var submitSeen SubmitRequest

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch {
		case r.Method == http.MethodGet && r.URL.Path == "/api/missions":
			json.NewEncoder(w).Encode(MissionList{
				Count: 1,
				Missions: []Mission{{
					ID:               "mis_1",
					Title:            "Build a client",
					VerificationType: "oracle",
					Status:           "open",
					RewardAIGEN:      200,
				}},
			})
		case r.Method == http.MethodGet && r.URL.Path == "/api/missions/mis_1":
			json.NewEncoder(w).Encode(Mission{
				ID:               "mis_1",
				Title:            "Build a client",
				Description:      "Implement OABP client",
				VerificationType: "oracle",
				Status:           "open",
			})
		case r.Method == http.MethodPost && r.URL.Path == "/api/missions/mis_1/submit":
			if err := json.NewDecoder(r.Body).Decode(&submitSeen); err != nil {
				t.Fatalf("decode submit body: %v", err)
			}
			json.NewEncoder(w).Encode(SubmitResponse{
				OK:              true,
				MissionID:       "mis_1",
				SubmissionID:    "sub_1",
				SubmissionCount: 1,
			})
		case r.Method == http.MethodGet && r.URL.Path == "/api/agents/agent-1/reputation":
			json.NewEncoder(w).Encode(AgentProfile{
				AgentID:      "agent-1",
				AIGENBalance: 120,
				Reputation: Reputation{
					AgentID: "agent-1",
					ELO:     1401,
					Rank:    "Newcomer",
					Wins:    1,
				},
			})
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	client, err := NewClient(server.URL)
	if err != nil {
		t.Fatalf("NewClient: %v", err)
	}
	ctx := context.Background()

	missions, err := client.ListMissions(ctx)
	if err != nil {
		t.Fatalf("ListMissions: %v", err)
	}
	if missions.Count != 1 || missions.Missions[0].ID != "mis_1" {
		t.Fatalf("unexpected missions: %+v", missions)
	}

	mission, err := client.GetMission(ctx, "mis_1")
	if err != nil {
		t.Fatalf("GetMission: %v", err)
	}
	if mission.Title != "Build a client" {
		t.Fatalf("unexpected mission: %+v", mission)
	}

	submit, err := client.SubmitSolution(ctx, "mis_1", SubmitRequest{
		SubmitterAgentID: "agent-1",
		SubmitterWallet:  "0xfBDB0Ad415e95c4843FD872FAc967459572910f1",
		Proof:            "https://github.com/example/oabp-go-client",
	})
	if err != nil {
		t.Fatalf("SubmitSolution: %v", err)
	}
	if !submit.OK || submit.SubmissionID != "sub_1" {
		t.Fatalf("unexpected submit response: %+v", submit)
	}
	if submitSeen.SubmitterAgentID != "agent-1" || submitSeen.Proof == "" {
		t.Fatalf("unexpected submit payload: %+v", submitSeen)
	}

	profile, err := client.GetAgentReputation(ctx, "agent-1")
	if err != nil {
		t.Fatalf("GetAgentReputation: %v", err)
	}
	if profile.AgentID != "agent-1" || profile.Reputation.ELO != 1401 {
		t.Fatalf("unexpected profile: %+v", profile)
	}
}

func TestValidation(t *testing.T) {
	if _, err := NewClient("not a url"); err == nil {
		t.Fatal("expected invalid URL error")
	}
	client, err := NewClient("https://cryptogenesis.duckdns.org")
	if err != nil {
		t.Fatalf("NewClient: %v", err)
	}
	if _, err := client.GetMission(context.Background(), ""); err == nil {
		t.Fatal("expected empty mission id error")
	}
	if _, err := client.SubmitSolution(context.Background(), "mis_1", SubmitRequest{}); err == nil {
		t.Fatal("expected invalid submit request error")
	}
}
