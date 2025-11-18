# Attack Wave Detection

TODO: Explain attack waves

The event payload for detected attack waves is structured as follows:

```ts
type DetectedAttackWave = {
  type: "detected_attack_wave";
  request: {
    ipAddress: string | undefined;
    userAgent: string | undefined;
    source: string;
  };
  attack: {
    metadata: Record<string, string>;
    user: User | undefined;
  };
  samples: {
    method: string;
    url: string;
  }[];
  agent: AgentInfo;
  time: number;
};
```

- `ipAddress` is the IP address from which the attack wave originated
- `userAgent` is the User-Agent header of the last request in the attack wave
- `source` is the name of the source where the request was detected (e.g. `"http.createServer"` in Node.js)
- `metadata` is an empty object for now

Later added:
- `samples` contains a list of suspicious requests that were sent from the same IP address within the attack wave time window. Each sample includes the HTTP method and URL of the request. The URL can be the full URL or just the path with query parameters (depending on the agent).
