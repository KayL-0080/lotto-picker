// Vercel Serverless Function: 동행복권 실시간 최신 회차 동기화 API
// GET /api/sync

export default async function handler(req, res) {
  // CORS 및 캐시 설정 (최신 데이터 1분 캐시, 백그라운드 재검증)
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=120');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    // 2002년 12월 7일 (1회차) 기준으로 현재 예상 회차 계산
    const firstDrawDate = new Date(Date.UTC(2002, 11, 7, 12, 0, 0));
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - firstDrawDate.getTime()) / (1000 * 60 * 60 * 24));
    let estimatedRound = Math.floor(diffDays / 7) + 1;

    // 만약 토요일 밤 20:45 이전이면 아직 이번 주 추첨 전일 수 있으므로 유연하게 조회
    const headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      'Accept': 'application/json, text/javascript, */*; q=0.01',
      'X-Requested-With': 'XMLHttpRequest'
    };

    // 최신 회차부터 역순으로 시도
    let lottoList = [];
    for (let roundCandidate of [estimatedRound, estimatedRound - 1, estimatedRound - 2]) {
      try {
        const targetUrl = `https://www.dhlottery.co.kr/lt645/selectPstLt645InfoNew.do?srchDir=center&srchLtEpsd=${roundCandidate}`;
        const resp = await fetch(targetUrl, { headers });
        if (resp.ok) {
          const json = await resp.json();
          if (json?.data?.list && json.data.list.length > 0) {
            lottoList = json.data.list;
            break;
          }
        }
      } catch (err) {
        console.warn(`Round ${roundCandidate} fetch error:`, err);
      }
    }

    if (!lottoList || lottoList.length === 0) {
      return res.status(500).json({
        success: false,
        error: '동행복권 API 응답을 가져오지 못했습니다.'
      });
    }

    // 최신 회차(가장 큰 ltEpsd) 추출
    const latestRaw = lottoList.reduce((max, cur) => Number(cur.ltEpsd) > Number(max.ltEpsd) ? cur : max, lottoList[0]);

    const latestRound = Number(latestRaw.ltEpsd);
    const numbers = [
      Number(latestRaw.tm1WnNo),
      Number(latestRaw.tm2WnNo),
      Number(latestRaw.tm3WnNo),
      Number(latestRaw.tm4WnNo),
      Number(latestRaw.tm5WnNo),
      Number(latestRaw.tm6WnNo)
    ].sort((a, b) => a - b);

    const bonus = Number(latestRaw.bnsWnNo);

    // 최근 5개 회차 요약 목록도 함께 제공
    const recentHistory = lottoList.slice(0, 5).map(item => ({
      round: Number(item.ltEpsd),
      date: item.ltRflYmd,
      numbers: [
        Number(item.tm1WnNo),
        Number(item.tm2WnNo),
        Number(item.tm3WnNo),
        Number(item.tm4WnNo),
        Number(item.tm5WnNo),
        Number(item.tm6WnNo)
      ].sort((a, b) => a - b),
      bonus: Number(item.bnsWnNo),
      winner_count: Number(item.rnk1WnNope || 0),
      first_prize: Number(item.rnk1WnAmt || 0)
    }));

    return res.status(200).json({
      success: true,
      latest_round: latestRound,
      next_round: latestRound + 1,
      latest_item: {
        round: latestRound,
        date: latestRaw.ltRflYmd,
        numbers: numbers,
        bonus: bonus,
        winner_count: Number(latestRaw.rnk1WnNope || 0),
        first_prize: Number(latestRaw.rnk1WnAmt || 0)
      },
      recent_history: recentHistory,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      error: error.message || '서버 오류가 발생했습니다.'
    });
  }
}
