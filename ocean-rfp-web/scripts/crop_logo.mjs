// GeoSR 로고를 헤더용으로 크롭: GeoSR + 지구본 + "GeoSystem Research Corporation"만 남기고
// 하단(|주|지오시스템리서치, www.GeoSR.com)은 제거 → src/assets/geosr-logo.png
// 원본 좌표(2362x1456)에서 직접 추출. (sharp trim은 투명 PNG에서 오작동하여 사용 안 함)
import sharp from 'sharp'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = '/mnt/c/Users/KJJEONG/Downloads/ci/Geosr logo.png'
const OUT = resolve(__dirname, '../src/assets/geosr-logo.png')

// 원본 분석으로 확정한 콘텐츠 경계
const left = 64 // GeoSR 좌측
const top = 170 // GeoSR 상단
const bottom = 938 // "GeoSystem Research Corporation" 아래 ~ 한글줄(964~) 직전
const width = 2233
const height = bottom - top

await sharp(SRC).extract({ left, top, width, height }).toFile(OUT)
const m = await sharp(OUT).metadata()
console.log('saved', OUT, `${m.width}x${m.height}`)
