package oabp

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
}

func NewClient(baseURL string, opts ...Option) (*Client, error) {
	if strings.TrimSpace(baseURL) == "" {
		return nil, fmt.Errorf("baseURL is required")
	}
	u, err := url.Parse(baseURL)
	if err != nil {
		return nil, fmt.Errorf("parse baseURL: %w", err)
	}
	if u.Scheme == "" || u.Host == "" {
		return nil, fmt.Errorf("baseURL must include scheme and host")
	}

	c := &Client{
		baseURL: strings.TrimRight(u.String(), "/"),
		httpClient: &http.Client{
			Timeout: 20 * time.Second,
		},
	}
	for _, opt := range opts {
		opt(c)
	}
	return c, nil
}

type Option func(*Client)

func WithHTTPClient(httpClient *http.Client) Option {
	return func(c *Client) {
		if httpClient != nil {
			c.httpClient = httpClient
		}
	}
}

type MissionList struct {
	Count    int       `json:"count"`
	Missions []Mission `json:"missions"`
}

type Mission struct {
	ID                        string         `json:"id"`
	Creator                   string         `json:"creator"`
	Title                     string         `json:"title"`
	Description               string         `json:"description"`
	Category                  string         `json:"category"`
	MissionType               string         `json:"mission_type"`
	Reward                    Reward         `json:"reward"`
	RewardAIGEN               int            `json:"reward_aigen"`
	VerificationType          string         `json:"verification_type"`
	VerificationParams        map[string]any `json:"verification_params"`
	Status                    string         `json:"status"`
	Deadline                  int64          `json:"deadline"`
	SubmissionCount           int            `json:"submission_count"`
	RequiredSubmitterTier     int            `json:"required_submitter_tier"`
	RequiredSubmitterTierName string         `json:"required_submitter_tier_name"`
	Submissions               []Submission   `json:"submissions,omitempty"`
	Resolution                any            `json:"resolution,omitempty"`
}

type Reward struct {
	Currency string `json:"currency"`
	Amount   int    `json:"amount"`
	Chain    string `json:"chain"`
}

type Submission struct {
	ID              string         `json:"id"`
	Submitter       string         `json:"submitter"`
	SubmitterWallet string         `json:"submitter_wallet"`
	Proof           string         `json:"proof"`
	Metadata        map[string]any `json:"metadata"`
	SubmittedAt     int64          `json:"submitted_at"`
	Status          string         `json:"status"`
}

type SubmitRequest struct {
	SubmitterAgentID string         `json:"submitter_agent_id"`
	SubmitterWallet  string         `json:"submitter_wallet,omitempty"`
	Proof            string         `json:"proof"`
	Metadata         map[string]any `json:"metadata,omitempty"`
}

type SubmitResponse struct {
	OK              bool   `json:"ok"`
	MissionID       string `json:"mission_id"`
	SubmissionID    string `json:"submission_id"`
	SubmissionCount int    `json:"submission_count"`
	Error           string `json:"error,omitempty"`
}

type AgentProfile struct {
	AgentID      string        `json:"agent_id"`
	AIGENBalance float64       `json:"aigen_balance"`
	Reputation   Reputation    `json:"reputation"`
	Progression  Progression   `json:"progression"`
	Missions     AgentMissions `json:"missions"`
	ProfileURL   string        `json:"profile_url"`
	BadgeURL     string        `json:"badge_url"`
}

type Reputation struct {
	AgentID string `json:"agent_id"`
	Score   int    `json:"score"`
	ELO     int    `json:"elo"`
	Rank    string `json:"rank"`
	Wins    int    `json:"wins"`
	Losses  int    `json:"losses"`
}

type Progression struct {
	CurrentRank     string `json:"current_rank"`
	CurrentELO      int    `json:"current_elo"`
	NextRank        string `json:"next_rank"`
	ELOPointsToNext int    `json:"elo_points_to_next"`
}

type AgentMissions struct {
	Created    int     `json:"created"`
	Submitted  int     `json:"submitted"`
	Won        int     `json:"won"`
	WinRatePct float64 `json:"win_rate_pct"`
}

func (c *Client) ListMissions(ctx context.Context) (*MissionList, error) {
	var out MissionList
	if err := c.do(ctx, http.MethodGet, "/api/missions", nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *Client) GetMission(ctx context.Context, id string) (*Mission, error) {
	if strings.TrimSpace(id) == "" {
		return nil, fmt.Errorf("mission id is required")
	}
	var out Mission
	if err := c.do(ctx, http.MethodGet, "/api/missions/"+url.PathEscape(id), nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *Client) SubmitSolution(ctx context.Context, missionID string, req SubmitRequest) (*SubmitResponse, error) {
	if strings.TrimSpace(missionID) == "" {
		return nil, fmt.Errorf("mission id is required")
	}
	if strings.TrimSpace(req.SubmitterAgentID) == "" {
		return nil, fmt.Errorf("submitter agent id is required")
	}
	if strings.TrimSpace(req.Proof) == "" {
		return nil, fmt.Errorf("proof is required")
	}

	var out SubmitResponse
	path := "/api/missions/" + url.PathEscape(missionID) + "/submit"
	if err := c.do(ctx, http.MethodPost, path, req, &out); err != nil {
		if !isNotFound(err) {
			return nil, err
		}
		fallbackPath := "/missions/" + url.PathEscape(missionID) + "/submit"
		if err := c.do(ctx, http.MethodPost, fallbackPath, req, &out); err != nil {
			return nil, err
		}
	}
	if out.Error != "" {
		return &out, fmt.Errorf(out.Error)
	}
	return &out, nil
}

func (c *Client) GetAgentReputation(ctx context.Context, agentID string) (*AgentProfile, error) {
	if strings.TrimSpace(agentID) == "" {
		return nil, fmt.Errorf("agent id is required")
	}
	var out AgentProfile
	path := "/api/agents/" + url.PathEscape(agentID) + "/reputation"
	if err := c.do(ctx, http.MethodGet, path, nil, &out); err != nil {
		if !isNotFound(err) {
			return nil, err
		}
		fallbackPath := "/api/agents/" + url.PathEscape(agentID)
		if err := c.do(ctx, http.MethodGet, fallbackPath, nil, &out); err != nil {
			return nil, err
		}
	}
	return &out, nil
}

func (c *Client) do(ctx context.Context, method, path string, body any, out any) error {
	var reader io.Reader
	if body != nil {
		payload, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("marshal request: %w", err)
		}
		reader = bytes.NewReader(payload)
	}

	httpReq, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, reader)
	if err != nil {
		return err
	}
	httpReq.Header.Set("Accept", "application/json")
	if body != nil {
		httpReq.Header.Set("Content-Type", "application/json")
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		return fmt.Errorf("%s %s: status %d: %s", method, path, resp.StatusCode, strings.TrimSpace(string(data)))
	}
	if out == nil || len(data) == 0 {
		return nil
	}
	if err := json.Unmarshal(data, out); err != nil {
		return fmt.Errorf("decode response: %w", err)
	}
	return nil
}

func isNotFound(err error) bool {
	return err != nil && strings.Contains(err.Error(), "status 404")
}
