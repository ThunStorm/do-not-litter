export const placeTypeLabels: Record<string, string> = {
  SCENIC_AREA: '景点', RESTAURANT: '餐饮', NEIGHBORHOOD: '街区', PEDESTRIAN_STREET: '步行街', BUSINESS_DISTRICT: '商圈', MARKET: '市集', PARK: '公园', MUSEUM: '博物馆', TEMPLE: '寺庙', VILLAGE: '村落', TOWN: '古镇/城镇', LANDMARK: '地标', ACCOMMODATION: '住宿', HOTEL: '住宿', TRANSIT: '交通', TRANSPORT: '交通', OTHER: '其他', UNKNOWN: '其他',
}
export const seasonLabels: Record<string, string> = { SPRING: '春季', SUMMER: '夏季', AUTUMN: '秋季', WINTER: '冬季' }
export const segmentLabels: Record<string, string> = { EARLY: '上旬', MID: '中旬', LATE: '下旬' }
export const timeLabels: Record<string, string> = { EARLY_MORNING: '清晨', MORNING: '上午', NOON: '中午', AFTERNOON: '下午', SUNSET: '日落', EVENING: '晚间', NIGHT: '夜间', BREAKFAST: '早餐', LUNCH: '午餐', DINNER: '晚餐', LATE_NIGHT: '深夜' }
export const periodTypeLabels: Record<string, string> = { BEST_VISIT: '适宜到访', BEST_VIEWING: '最佳观赏期', HIGH_WATER: '丰水期', LOW_WATER: '枯水期', FISHING_CLOSURE: '渔业时段', SEASONAL_CLOSURE: '季节性开放', BLOOM: '花期', FOLIAGE: '红叶期', SNOW: '雪季', MIGRATION: '候鸟/迁徙期', WEATHER_SEASON: '气候季节', PEAK_SEASON: '旺季', OFF_SEASON: '淡季', OTHER: '其他时段' }
export const suitabilityLabels: Record<string, string> = { RECOMMENDED: '推荐', AVOID: '建议避开', RESTRICTED: '限制', INFORMATIONAL: '时段信息' }
export const stateLabels: Record<string, string> = { DISCOVERED: '新发现', SAVED: '想去', PLANNED: '已计划', VISITED: '去过', DISMISSED: '不感兴趣' }
export const labelPlaceType = (value: string) => placeTypeLabels[value] ?? '其他'
export const visitWindowLabel = (value: { season?: string | null; month?: number | null; month_segment?: string | null; day_time_slot?: string | null; period_type?: string; suitability?: string }) => [value.suitability && suitabilityLabels[value.suitability], value.period_type && periodTypeLabels[value.period_type], value.season && seasonLabels[value.season], value.month && `${value.month}月${value.month_segment ? segmentLabels[value.month_segment] : ''}`, value.day_time_slot && timeLabels[value.day_time_slot]].filter(Boolean).join(' · ') || '时间信息'
