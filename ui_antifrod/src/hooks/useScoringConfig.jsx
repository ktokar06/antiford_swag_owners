import { useCallback, useEffect, useState } from 'react';
import { rulesApi } from '@/api/rules';
import { DEFAULT_POLICY } from '@/libs/scoring';

export default function useScoringConfig() {
  const [rules, setRules] = useState([]);
  const [policy, setPolicy] = useState(DEFAULT_POLICY);
  const [policyRecord, setPolicyRecord] = useState(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const policyData = await rulesApi.getPolicy();
      setPolicyRecord(policyData || null);
      setPolicy(policyData || DEFAULT_POLICY);
    } catch {
      setRules([]);
      setPolicy(DEFAULT_POLICY);
      setPolicyRecord(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return { rules, policy, policyRecord, loading, reload };
}
