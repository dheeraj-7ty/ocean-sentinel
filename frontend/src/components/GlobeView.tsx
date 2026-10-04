import React, { useEffect, useRef, useState, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import {
  Compass,
  Maximize2,
  Minimize2,
  RotateCcw,
  Crosshair,
  Info,
  MapPin,
  LocateFixed,
  X,
  Target,
  ShieldAlert,
} from 'lucide-react'
import type {
  CandidateVesselHypothesis,
  EvidenceItem,
  InvestigationRun,
  JobResultResponse,
  LayerVisibility,
  SelectedLocation,
} from '../types/api'

interface GlobeViewProps {
  result: JobResultResponse | null
  investigation?: InvestigationRun | null
  aoiGeometry?: any
  observationFootprint?: any
  selectedEvidenceId: string | null
  onSelectEvidence: (id: string | null) => void
  selectedLocation: SelectedLocation | null
  onSelectLocation: (location: SelectedLocation | null) => void
  layers: LayerVisibility
  isLoading: boolean
  isQuarantined?: boolean
}

// Convert Lat/Lon (degrees) to 3D Cartesian coordinates on sphere of radius R
export function latLonToVector3(lat: number, lon: number, radius = 100, altitude = 0): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)
  const r = radius + altitude

  const x = -(r * Math.sin(phi) * Math.cos(theta))
  const z = r * Math.sin(phi) * Math.sin(theta)
  const y = r * Math.cos(phi)

  return new THREE.Vector3(x, y, z)
}

// Convert 3D Cartesian coordinates on sphere back to Lat/Lon
export function vector3ToLatLon(v: THREE.Vector3, _radius = 100): { lat: number; lon: number } {
  const norm = v.clone().normalize()
  const lat = 90 - (Math.acos(norm.y) * 180) / Math.PI
  let lon = (Math.atan2(norm.z, -norm.x) * 180) / Math.PI - 180
  while (lon < -180) lon += 360
  while (lon > 180) lon += 360
  return { lat, lon }
}

export const GlobeView: React.FC<GlobeViewProps> = ({
  result,
  investigation,
  aoiGeometry,
  observationFootprint,
  selectedEvidenceId,
  onSelectEvidence,
  selectedLocation,
  onSelectLocation,
  layers,
  isLoading,
  isQuarantined = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const globeMeshRef = useRef<THREE.Mesh | null>(null)

  // Layer groups
  const sarGroupRef = useRef<THREE.Group>(new THREE.Group())
  const temporalGroupRef = useRef<THREE.Group>(new THREE.Group())
  const driftGroupRef = useRef<THREE.Group>(new THREE.Group())
  const originGroupRef = useRef<THREE.Group>(new THREE.Group())
  const aisGroupRef = useRef<THREE.Group>(new THREE.Group())
  const fusionGroupRef = useRef<THREE.Group>(new THREE.Group())
  const userLocationGroupRef = useRef<THREE.Group>(new THREE.Group())
  const aoiGroupRef = useRef<THREE.Group>(new THREE.Group())
  const footprintGroupRef = useRef<THREE.Group>(new THREE.Group())
  const highlightGroupRef = useRef<THREE.Group>(new THREE.Group())

  const interactiveObjectsRef = useRef<THREE.Object3D[]>([])
  const [hudCoords, setHudCoords] = useState<{ lat: number; lon: number }>({
    lat: 32.2,
    lon: 30.6,
  })
  const [cameraAltitudeKm, setCameraAltitudeKm] = useState<number>(320)
  const [hoveredFeature, setHoveredFeature] = useState<{ id: string; name: string } | null>(null)
  const isQuarantinedRef = useRef(isQuarantined)

  useEffect(() => {
    isQuarantinedRef.current = isQuarantined
  }, [isQuarantined])

  // Fly camera smoothly to target
  const flyTo = useCallback((targetLat: number, targetLon: number, distance = 135) => {
    if (!cameraRef.current || !controlsRef.current) return
    const targetPos = latLonToVector3(targetLat, targetLon, 100)
    const camPos = latLonToVector3(targetLat - 4, targetLon, distance)

    const startPos = cameraRef.current.position.clone()
    const startTarget = controlsRef.current.target.clone()
    const startTime = performance.now()
    const duration = 1000 // ms

    const animateFly = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      const ease = 0.5 - Math.cos(progress * Math.PI) / 2

      cameraRef.current?.position.lerpVectors(startPos, camPos, ease)
      controlsRef.current?.target.lerpVectors(startTarget, targetPos, ease)
      controlsRef.current?.update()

      if (progress < 1) {
        requestAnimationFrame(animateFly)
      }
    }
    requestAnimationFrame(animateFly)
  }, [])

  // Initialize Three.js scene
  useEffect(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    const width = container.clientWidth
    const height = container.clientHeight

    // Scene
    const scene = new THREE.Scene()
    sceneRef.current = scene
    scene.background = new THREE.Color(0x040711)

    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 3000)
    camera.position.set(0, 60, 165)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    rendererRef.current = renderer
    container.appendChild(renderer.domElement)

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.minDistance = 105
    controls.maxDistance = 550
    const defaultTarget = latLonToVector3(32.18, 30.65, 100)
    controls.target.copy(defaultTarget)
    controlsRef.current = controls

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9)
    scene.add(ambientLight)

    const sunLight = new THREE.DirectionalLight(0xdbeafe, 1.3)
    sunLight.position.set(300, 200, 300)
    scene.add(sunLight)

    const rimLight = new THREE.DirectionalLight(0x00f2fe, 0.7)
    rimLight.position.set(-200, -100, -200)
    scene.add(rimLight)

    // 1. Globe Sphere (Base Ocean Surface)
    const globeRadius = 100
    const globeGeo = new THREE.SphereGeometry(globeRadius, 64, 64)
    const globeMat = new THREE.MeshStandardMaterial({
      color: 0x071124,
      roughness: 0.85,
      metalness: 0.15,
      emissive: 0x020712,
    })
    const globeMesh = new THREE.Mesh(globeGeo, globeMat)
    globeMesh.name = 'BASE_GLOBE'
    globeMeshRef.current = globeMesh
    scene.add(globeMesh)

    // 2. Atmospheric Glow Ring
    const atmosphereGeo = new THREE.SphereGeometry(globeRadius * 1.018, 64, 64)
    const atmosphereMat = new THREE.MeshBasicMaterial({
      color: 0x00f2fe,
      transparent: true,
      opacity: 0.09,
      side: THREE.BackSide,
    })
    const atmosphereMesh = new THREE.Mesh(atmosphereGeo, atmosphereMat)
    scene.add(atmosphereMesh)

    // 3. Graticule Lines (Parallels and Meridians)
    const graticuleGroup = new THREE.Group()
    const graticuleMat = new THREE.LineBasicMaterial({
      color: 0x1e3a8a,
      transparent: true,
      opacity: 0.35,
    })
    const majorGraticuleMat = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.5,
    })

    // Parallels every 15 degrees (Equator highlighted)
    for (let lat = -75; lat <= 75; lat += 15) {
      const points: THREE.Vector3[] = []
      for (let lon = 0; lon <= 360; lon += 5) {
        points.push(latLonToVector3(lat, lon, globeRadius, 0.05))
      }
      const lineGeo = new THREE.BufferGeometry().setFromPoints(points)
      graticuleGroup.add(new THREE.Line(lineGeo, lat === 0 ? majorGraticuleMat : graticuleMat))
    }

    // Meridians every 15 degrees (Prime Meridian highlighted)
    for (let lon = 0; lon < 360; lon += 15) {
      const points: THREE.Vector3[] = []
      for (let lat = -85; lat <= 85; lat += 5) {
        points.push(latLonToVector3(lat, lon, globeRadius, 0.05))
      }
      const lineGeo = new THREE.BufferGeometry().setFromPoints(points)
      graticuleGroup.add(new THREE.Line(lineGeo, lon === 0 ? majorGraticuleMat : graticuleMat))
    }
    scene.add(graticuleGroup)

    // 4. Vector Continental Coastline Context Outlines (Enhanced Geographic Boundaries)
    const coastlineGroup = new THREE.Group()
    const primaryCoastlineMat = new THREE.LineBasicMaterial({
      color: 0x64748b,
      transparent: true,
      opacity: 0.95,
    })

    const sampleCoastlines: [number, number][][] = [
      // Mediterranean basin / North Africa & Southern Europe coastline
      [
        [31.2, 29.9], [31.5, 31.0], [31.8, 32.5], [32.5, 34.5], [33.5, 35.2],
        [35.0, 36.0], [36.5, 35.8], [36.8, 33.0], [36.5, 30.0], [37.5, 27.0],
        [39.0, 26.0], [40.5, 23.0], [40.0, 20.0], [42.0, 19.0], [45.0, 13.5],
        [43.5, 10.5], [43.0, 6.0], [41.0, 2.0], [37.0, -1.5], [36.0, -5.5],
        [35.5, -5.3], [35.8, -2.0], [36.8, 3.0], [37.0, 10.0], [34.0, 10.5],
        [33.0, 12.0], [32.0, 15.0], [32.2, 20.0], [32.0, 24.0], [31.3, 27.0],
        [31.2, 29.9],
      ],
      // Black Sea
      [
        [42.0, 28.5], [44.0, 29.0], [46.5, 31.0], [46.0, 34.0], [45.0, 36.5],
        [44.5, 38.0], [42.0, 41.5], [41.0, 38.0], [41.2, 31.0], [42.0, 28.5],
      ],
      // Red Sea & Arabian Peninsula
      [
        [28.0, 34.0], [22.0, 38.0], [12.0, 44.0], [12.5, 45.0], [15.0, 52.0],
        [22.0, 59.5], [26.0, 56.5], [29.0, 48.5], [30.0, 48.0], [27.0, 50.0],
        [24.0, 53.0], [24.0, 56.0], [20.0, 42.0], [27.5, 35.5], [28.0, 34.0],
      ],
      // Africa perimeter
      [
        [35.5, -5.3], [30.0, -10.0], [20.0, -17.0], [10.0, -15.0], [5.0, 0.0],
        [4.0, 9.0], [-5.0, 12.0], [-15.0, 12.0], [-34.5, 18.5], [-33.0, 28.0],
        [-25.0, 33.0], [-10.0, 40.0], [0.0, 42.0], [12.0, 51.0], [12.0, 44.0],
        [22.0, 38.0], [28.0, 34.0], [31.2, 32.2], [32.0, 24.0],
      ],
      // Western Europe & Atlantic
      [
        [36.0, -5.5], [37.0, -9.0], [43.5, -9.0], [43.5, -2.0], [47.5, -3.0],
        [49.5, -1.5], [51.0, 2.0], [53.5, 7.0], [55.0, 8.5], [57.0, 12.0],
        [60.0, 5.0], [62.0, 7.0], [70.0, 25.0],
      ],
      // British Isles
      [
        [50.0, -5.0], [52.0, 1.5], [58.5, -3.0], [58.5, -5.5], [55.0, -5.0],
        [51.5, -3.5], [50.0, -5.0],
      ],
    ]

    sampleCoastlines.forEach((ring) => {
      const points = ring.map(([lat, lon]) => latLonToVector3(lat, lon, globeRadius, 0.08))
      const geo = new THREE.BufferGeometry().setFromPoints(points)
      coastlineGroup.add(new THREE.Line(geo, primaryCoastlineMat))
    })
    scene.add(coastlineGroup)

    // Mount layer groups to scene
    scene.add(sarGroupRef.current)
    scene.add(temporalGroupRef.current)
    scene.add(driftGroupRef.current)
    scene.add(originGroupRef.current)
    scene.add(aisGroupRef.current)
    scene.add(fusionGroupRef.current)
    scene.add(userLocationGroupRef.current)
    scene.add(aoiGroupRef.current)
    scene.add(footprintGroupRef.current)
    scene.add(highlightGroupRef.current)

    // Raycaster for mouse interaction & HUD coordinates
    const raycaster = new THREE.Raycaster()
    const mouse = new THREE.Vector2()

    const handleMouseMove = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

      raycaster.setFromCamera(mouse, camera)
      const intersects = raycaster.intersectObject(globeMesh)
      if (intersects.length > 0) {
        const point = intersects[0].point
        const { lat, lon } = vector3ToLatLon(point, globeRadius)
        setHudCoords({ lat, lon })
      }

      // Check hover over interactive evidence markers
      if (interactiveObjectsRef.current.length > 0) {
        const featureIntersects = raycaster.intersectObjects(
          interactiveObjectsRef.current,
          true
        )
        if (featureIntersects.length > 0) {
          let topObj = featureIntersects[0].object
          while (topObj.parent && !topObj.userData?.evidenceId) {
            topObj = topObj.parent
          }
          if (topObj.userData?.evidenceId) {
            if (isQuarantinedRef.current) {
              setHoveredFeature({
                id: topObj.userData.evidenceId,
                name: `[QUARANTINED] ${topObj.userData.label || topObj.userData.evidenceId}`,
              })
              renderer.domElement.style.cursor = 'not-allowed'
              return
            }
            setHoveredFeature({
              id: topObj.userData.evidenceId,
              name: topObj.userData.label || topObj.userData.evidenceId,
            })
            renderer.domElement.style.cursor = 'pointer'
            return
          }
        }
      }
      setHoveredFeature(null)
      renderer.domElement.style.cursor = 'grab'
    }

    // Globe Click Handler: Distinguish Evidence Hit vs User-Selected Location Hit
    const handleClick = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

      raycaster.setFromCamera(mouse, camera)

      // 1. Check if an interactive evidence/vessel marker was clicked
      if (interactiveObjectsRef.current.length > 0) {
        const featureIntersects = raycaster.intersectObjects(
          interactiveObjectsRef.current,
          true
        )
        if (featureIntersects.length > 0) {
          let topObj = featureIntersects[0].object
          while (topObj.parent && !topObj.userData?.evidenceId) {
            topObj = topObj.parent
          }
          if (topObj.userData?.evidenceId) {
            // When quarantined: strictly neutralize evidence click.
            // Do NOT select evidence, do NOT flyTo, and do NOT fall through to operator-reference selection!
            if (isQuarantinedRef.current) {
              return
            }
            onSelectEvidence(topObj.userData.evidenceId)
            if (topObj.userData.lat && topObj.userData.lon) {
              flyTo(topObj.userData.lat, topObj.userData.lon, 130)
            }
            return
          }
        }
      }

      // 2. Only if no interactive evidence object was clicked, check if genuine empty globe surface was clicked
      const globeHits = raycaster.intersectObject(globeMesh)
      if (globeHits.length > 0) {
        const hitPoint = globeHits[0].point
        const { lat, lon } = vector3ToLatLon(hitPoint, globeRadius)
        // Set user-selected location (pure operator reference coordinate, NOT evidence)
        onSelectLocation({
          lat: Number(lat.toFixed(4)),
          lon: Number(lon.toFixed(4)),
          selectedAtUtc: new Date().toISOString(),
        })
      }
    }

    renderer.domElement.addEventListener('mousemove', handleMouseMove)
    renderer.domElement.addEventListener('click', handleClick)

    // Animation Loop
    let animationFrameId: number
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate)
      controls.update()

      // Calculate camera altitude relative to sphere surface
      const camDist = camera.position.distanceTo(new THREE.Vector3(0, 0, 0))
      const altKm = Math.round((camDist - globeRadius) * 5)
      setCameraAltitudeKm(Math.max(10, altKm))

      renderer.render(scene, camera)
    }
    animate()

    // Resize Observer
    const handleResize = () => {
      if (!containerRef.current || !rendererRef.current || !cameraRef.current) return
      const w = containerRef.current.clientWidth
      const h = containerRef.current.clientHeight
      cameraRef.current.aspect = w / h
      cameraRef.current.updateProjectionMatrix()
      rendererRef.current.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)

    // Initial camera position towards incident area
    flyTo(32.18, 30.65, 140)

    return () => {
      cancelAnimationFrame(animationFrameId)
      window.removeEventListener('resize', handleResize)
      renderer.domElement.removeEventListener('mousemove', handleMouseMove)
      renderer.domElement.removeEventListener('click', handleClick)
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [flyTo, onSelectEvidence, onSelectLocation])

  // Update Layer Visibility Toggles
  useEffect(() => {
    sarGroupRef.current.visible = layers.sar_detection
    temporalGroupRef.current.visible = layers.temporal_change
    driftGroupRef.current.visible = layers.drift_trajectory
    originGroupRef.current.visible = layers.drift_origin
    aisGroupRef.current.visible = layers.ais_tracks
    fusionGroupRef.current.visible = layers.fused_evidence
    aoiGroupRef.current.visible = layers.aoi_geometry ?? true
    footprintGroupRef.current.visible = layers.observation_footprint ?? true
  }, [layers])

  // 3D AOI & Observation Footprint Render & Lifecycle (Phase 7C)
  useEffect(() => {
    // Clear existing AOI children
    while (aoiGroupRef.current.children.length > 0) {
      const obj = aoiGroupRef.current.children[0]
      aoiGroupRef.current.remove(obj)
    }
    // Clear existing footprint children
    while (footprintGroupRef.current.children.length > 0) {
      const obj = footprintGroupRef.current.children[0]
      footprintGroupRef.current.remove(obj)
    }

    const R = 100

    // 1. Render AOI Geometry (USER_INPUT)
    let aoiCoords: [number, number][] | null = null
    const rawAoi = aoiGeometry || investigation?.request?.aoi
    const rawBbox = investigation?.request?.bbox

    if (rawAoi && rawAoi.type === 'Polygon' && Array.isArray(rawAoi.coordinates?.[0])) {
      aoiCoords = rawAoi.coordinates[0].map(([lon, lat]: [number, number]) => [lat, lon])
    } else if (rawBbox && Array.isArray(rawBbox) && rawBbox.length === 4) {
      const [w, s, e, n] = rawBbox
      aoiCoords = [
        [s, w],
        [s, e],
        [n, e],
        [n, w],
        [s, w],
      ]
    }

    if (aoiCoords && aoiCoords.length >= 4) {
      const points = aoiCoords.map(([lat, lon]) => latLonToVector3(lat, lon, R, 0.28))
      let centerLat = 0
      let centerLon = 0
      aoiCoords.slice(0, aoiCoords.length - 1).forEach(([lat, lon]) => {
        centerLat += lat
        centerLon += lon
      })
      const count = aoiCoords.length - 1
      centerLat /= count
      centerLon /= count

      const aoiGeo = new THREE.BufferGeometry().setFromPoints(points)
      const aoiMat = new THREE.LineBasicMaterial({
        color: 0x00f2fe,
        linewidth: 2,
      })
      const aoiLoop = new THREE.LineLoop(aoiGeo, aoiMat)
      aoiLoop.userData = {
        evidenceId: 'USER_AOI',
        label: 'OPERATOR AOI (USER_INPUT)',
        lat: centerLat,
        lon: centerLon,
        isUserInput: true,
      }
      aoiGroupRef.current.add(aoiLoop)
      interactiveObjectsRef.current.push(aoiLoop)

      // Corner target spheres
      points.slice(0, points.length - 1).forEach((pt) => {
        const cornerGeo = new THREE.SphereGeometry(0.5, 12, 12)
        const cornerMat = new THREE.MeshBasicMaterial({ color: 0x00f2fe })
        const cornerMesh = new THREE.Mesh(cornerGeo, cornerMat)
        cornerMesh.position.copy(pt)
        cornerMesh.userData = aoiLoop.userData
        aoiGroupRef.current.add(cornerMesh)
      })

      // Center marker
      const centerGeo = new THREE.SphereGeometry(0.8, 16, 16)
      const centerMat = new THREE.MeshBasicMaterial({ color: 0x00f2fe })
      const centerMesh = new THREE.Mesh(centerGeo, centerMat)
      centerMesh.position.copy(latLonToVector3(centerLat, centerLon, R, 0.32))
      centerMesh.userData = aoiLoop.userData
      aoiGroupRef.current.add(centerMesh)
      interactiveObjectsRef.current.push(centerMesh)

      // Auto-focus if investigation is present without full result
      if (!result && investigation) {
        flyTo(centerLat, centerLon, 135)
      }
    }

    // 2. Render Observation Footprint (REAL_REPOSITORY_EVIDENCE)
    let footprintCoords: [number, number][] | null = null
    const rawFootprint = observationFootprint || investigation?.evidence_state?.footprint
    const rawEvidenceBbox = investigation?.evidence_state?.bbox

    if (rawFootprint && rawFootprint.type === 'Polygon' && Array.isArray(rawFootprint.coordinates?.[0])) {
      footprintCoords = rawFootprint.coordinates[0].map(([lon, lat]: [number, number]) => [lat, lon])
    } else if (rawEvidenceBbox && Array.isArray(rawEvidenceBbox) && rawEvidenceBbox.length === 4) {
      const [w, s, e, n] = rawEvidenceBbox
      footprintCoords = [
        [s, w],
        [s, e],
        [n, e],
        [n, w],
        [s, w],
      ]
    }

    if (footprintCoords && footprintCoords.length >= 4) {
      const points = footprintCoords.map(([lat, lon]) => latLonToVector3(lat, lon, R, 0.35))
      let centerLat = 0
      let centerLon = 0
      footprintCoords.slice(0, footprintCoords.length - 1).forEach(([lat, lon]) => {
        centerLat += lat
        centerLon += lon
      })
      const count = footprintCoords.length - 1
      centerLat /= count
      centerLon /= count

      const fpGeo = new THREE.BufferGeometry().setFromPoints(points)
      const fpMat = new THREE.LineBasicMaterial({
        color: 0xf59e0b, // Amber / gold
        linewidth: 2,
      })
      const fpLoop = new THREE.LineLoop(fpGeo, fpMat)
      fpLoop.userData = {
        evidenceId: 'OBSERVATION_FOOTPRINT',
        label: 'SENTINEL-1 SAR OBSERVATION FOOTPRINT (REAL_REPOSITORY_EVIDENCE)',
        lat: centerLat,
        lon: centerLon,
        isRealEvidence: true,
      }
      footprintGroupRef.current.add(fpLoop)
      interactiveObjectsRef.current.push(fpLoop)

      // Corner target spheres
      points.slice(0, points.length - 1).forEach((pt) => {
        const cornerGeo = new THREE.SphereGeometry(0.5, 12, 12)
        const cornerMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b })
        const cornerMesh = new THREE.Mesh(cornerGeo, cornerMat)
        cornerMesh.position.copy(pt)
        cornerMesh.userData = fpLoop.userData
        footprintGroupRef.current.add(cornerMesh)
      })

      // Center marker
      const centerGeo = new THREE.SphereGeometry(0.8, 16, 16)
      const centerMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b })
      const centerMesh = new THREE.Mesh(centerGeo, centerMat)
      centerMesh.position.copy(latLonToVector3(centerLat, centerLon, R, 0.38))
      centerMesh.userData = fpLoop.userData
      footprintGroupRef.current.add(centerMesh)
      interactiveObjectsRef.current.push(centerMesh)
    }
  }, [aoiGeometry, observationFootprint, investigation, flyTo, result])

  // 3D User Location Marker Render & Lifecycle
  useEffect(() => {
    // Clear existing user location marker
    while (userLocationGroupRef.current.children.length > 0) {
      userLocationGroupRef.current.remove(userLocationGroupRef.current.children[0])
    }

    if (!selectedLocation) return

    const R = 100
    const { lat, lon } = selectedLocation
    const pos = latLonToVector3(lat, lon, R, 0.4)

    // 1. Concentric pulsing target rings
    const ringGeo1 = new THREE.RingGeometry(1.0, 1.5, 32)
    const ringMat1 = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9,
    })
    const ringMesh1 = new THREE.Mesh(ringGeo1, ringMat1)
    ringMesh1.position.copy(pos)
    ringMesh1.lookAt(new THREE.Vector3(0, 0, 0))
    userLocationGroupRef.current.add(ringMesh1)

    const ringGeo2 = new THREE.RingGeometry(1.8, 2.2, 32)
    const ringMat2 = new THREE.MeshBasicMaterial({
      color: 0x00f2fe,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.7,
    })
    const ringMesh2 = new THREE.Mesh(ringGeo2, ringMat2)
    ringMesh2.position.copy(pos)
    ringMesh2.lookAt(new THREE.Vector3(0, 0, 0))
    userLocationGroupRef.current.add(ringMesh2)

    // 2. Central target sphere
    const centerGeo = new THREE.SphereGeometry(0.6, 16, 16)
    const centerMat = new THREE.MeshBasicMaterial({ color: 0x00f2fe })
    const centerMesh = new THREE.Mesh(centerGeo, centerMat)
    centerMesh.position.copy(pos)
    userLocationGroupRef.current.add(centerMesh)

    // 3. Radial pin line projecting from surface
    const pinTop = latLonToVector3(lat, lon, R, 4.0)
    const pinGeo = new THREE.BufferGeometry().setFromPoints([pos, pinTop])
    const pinMat = new THREE.LineBasicMaterial({ color: 0x00f2fe, linewidth: 2 })
    const pinLine = new THREE.Line(pinGeo, pinMat)
    userLocationGroupRef.current.add(pinLine)
  }, [selectedLocation])

  // Clear & Rebuild Layers when result changes
  useEffect(() => {
    // Clear existing layer children
    const clearGroup = (group: THREE.Group) => {
      while (group.children.length > 0) {
        const obj = group.children[0]
        group.remove(obj)
      }
    }

    clearGroup(sarGroupRef.current)
    clearGroup(temporalGroupRef.current)
    clearGroup(driftGroupRef.current)
    clearGroup(originGroupRef.current)
    clearGroup(aisGroupRef.current)
    clearGroup(fusionGroupRef.current)
    interactiveObjectsRef.current = []

    if (!result) return

    const R = 100

    // Auto-focus event when result is loaded (uses authentic scenario centroid if available)
    const targetLat = result.scenario_metadata?.centroid ? result.scenario_metadata.centroid[1] : 32.18
    const targetLon = result.scenario_metadata?.centroid ? result.scenario_metadata.centroid[0] : 30.65
    flyTo(targetLat, targetLon, 135)

    // 1. Render Candidate Spill Hypotheses & Evidence Ledger
    if (result.evidence_ledger && result.evidence_ledger.length > 0) {
      result.evidence_ledger.forEach((item: EvidenceItem) => {
        const geom = item.spatial_geometry
        if (!geom) return

        // SAR Detection or Temporal Change Polygons
        if (geom.type === 'Polygon' || geom.type === 'MultiPolygon') {
          const polys = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates
          polys.forEach((ringCoords: any) => {
            const exteriorRing = ringCoords[0]
            if (!Array.isArray(exteriorRing) || exteriorRing.length === 0) return

            const points: THREE.Vector3[] = []
            let centerLat = 0
            let centerLon = 0

            exteriorRing.forEach(([lon, lat]: [number, number]) => {
              points.push(latLonToVector3(lat, lon, R, 0.18))
              centerLat += lat
              centerLon += lon
            })
            centerLat /= exteriorRing.length
            centerLon /= exteriorRing.length

            // Determine color based on evidence type
            let color = 0x00f2fe
            let targetGroup = sarGroupRef.current

            if (item.evidence_type === 'TEMPORAL_CHANGE') {
              targetGroup = temporalGroupRef.current
              color = item.source_id?.includes('persistent') ? 0xa855f7 : 0xec4899
            } else if (item.evidence_type === 'DRIFT_ORIGIN_HYPOTHESIS') {
              targetGroup = originGroupRef.current
              color = 0xea580c
            }

            // Outline loop
            const loopGeo = new THREE.BufferGeometry().setFromPoints(points)
            const loopMat = new THREE.LineBasicMaterial({
              color,
              linewidth: 2,
            })
            const lineLoop = new THREE.LineLoop(loopGeo, loopMat)
            lineLoop.userData = {
              evidenceId: item.evidence_id,
              label: `${item.evidence_type} (${item.evidence_id.substring(0, 18)}...)`,
              lat: centerLat,
              lon: centerLon,
            }
            targetGroup.add(lineLoop)
            interactiveObjectsRef.current.push(lineLoop)

            // Center marker
            const markerGeo = new THREE.SphereGeometry(0.6, 12, 12)
            const markerMat = new THREE.MeshBasicMaterial({ color })
            const markerMesh = new THREE.Mesh(markerGeo, markerMat)
            markerMesh.position.copy(latLonToVector3(centerLat, centerLon, R, 0.22))
            markerMesh.userData = lineLoop.userData
            targetGroup.add(markerMesh)
            interactiveObjectsRef.current.push(markerMesh)
          })
        }

        // Drift Trajectories: LineStrings or MultiLineStrings
        if (geom.type === 'LineString' || geom.type === 'MultiLineString') {
          const lines = geom.type === 'LineString' ? [geom.coordinates] : geom.coordinates
          lines.forEach((coords: any) => {
            const points: THREE.Vector3[] = []
            coords.forEach(([lon, lat]: [number, number]) => {
              points.push(latLonToVector3(lat, lon, R, 0.14))
            })
            if (points.length > 1) {
              const lineGeo = new THREE.BufferGeometry().setFromPoints(points)
              const lineMat = new THREE.LineBasicMaterial({
                color: 0xf59e0b,
                transparent: true,
                opacity: 0.9,
              })
              const lineObj = new THREE.Line(lineGeo, lineMat)
              lineObj.userData = {
                evidenceId: item.evidence_id,
                label: `Drift Trajectory (${item.evidence_id})`,
                lat: coords[0][1],
                lon: coords[0][0],
              }
              driftGroupRef.current.add(lineObj)
              interactiveObjectsRef.current.push(lineObj)
            }
          })
        }
      })
    }

    // 2. Render Candidate Origin Region from candidate_spill_hypotheses if present
    if (result.candidate_spill_hypotheses) {
      result.candidate_spill_hypotheses.forEach((hyp) => {
        if (hyp.spatial_geometry?.coordinates) {
          const exterior = hyp.spatial_geometry.coordinates[0]
          if (Array.isArray(exterior) && exterior.length > 2) {
            const points = exterior.map(([lon, lat]: [number, number]) =>
              latLonToVector3(lat, lon, R, 0.24)
            )
            const lineGeo = new THREE.BufferGeometry().setFromPoints(points)
            const lineMat = new THREE.LineBasicMaterial({
              color: 0xea580c,
              linewidth: 2,
            })
            const line = new THREE.LineLoop(lineGeo, lineMat)
            line.userData = {
              evidenceId: hyp.hypothesis_id,
              label: `Origin Hypothesis: ${hyp.hypothesis_id}`,
              lat: exterior[0][1],
              lon: exterior[0][0],
            }
            originGroupRef.current.add(line)
            interactiveObjectsRef.current.push(line)
          }
        }
      })
    }

    // 3. Render Candidate Vessels and AIS Tracks
    if (result.candidate_vessel_hypotheses) {
      result.candidate_vessel_hypotheses.forEach((vessel: CandidateVesselHypothesis) => {
        let vLat = 32.2
        let vLon = 30.65
        let color = 0x3b82f6 // default blue

        if (vessel.mmsi === '368123450') {
          // MT_HORIZON_STAR (Supported)
          vLat = 32.215
          vLon = 30.672
          color = 0x10b981 // emerald (high compatibility)
        } else if (vessel.mmsi === '368777880') {
          // GULF_SUPPLIER_VII (Supported)
          vLat = 32.198
          vLon = 30.655
          color = 0x38bdf8 // cyan/sky
        } else if (vessel.mmsi === '369555660') {
          // GLITCH_RUNNER (Conflicting)
          vLat = 32.245
          vLon = 30.71
          color = 0xef4444 // rose/red
        } else if (vessel.mmsi === '366333440') {
          // SEA_PROWLER (Telemetry gap)
          vLat = 32.16
          vLon = 30.61
          color = 0x94a3b8 // grey
        } else {
          vLat = 32.12
          vLon = 30.55
          color = 0x64748b
        }

        const vPos = latLonToVector3(vLat, vLon, R, 0.35)

        // Vessel 3D Marker: Larger cone shape for clear visibility at default zoom
        const markerGeo = new THREE.ConeGeometry(0.9, 2.2, 4)
        markerGeo.rotateX(Math.PI / 2)
        const markerMat = new THREE.MeshStandardMaterial({
          color,
          roughness: 0.3,
          metalness: 0.8,
          emissive: color,
          emissiveIntensity: 0.4,
        })
        const markerMesh = new THREE.Mesh(markerGeo, markerMat)
        markerMesh.position.copy(vPos)
        markerMesh.lookAt(new THREE.Vector3(0, 0, 0))

        markerMesh.userData = {
          evidenceId: vessel.hypothesis_id,
          label: `${vessel.vessel_name || vessel.mmsi} (Score: ${vessel.evidence_compatibility_score.toFixed(2)})`,
          lat: vLat,
          lon: vLon,
          status: vessel.overall_status,
        }

        aisGroupRef.current.add(markerMesh)
        interactiveObjectsRef.current.push(markerMesh)

        // Dual pulsing halo rings around candidate vessel
        const ringGeo1 = new THREE.RingGeometry(0.9, 1.4, 16)
        const ringMat1 = new THREE.MeshBasicMaterial({
          color,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.7,
        })
        const ringMesh1 = new THREE.Mesh(ringGeo1, ringMat1)
        ringMesh1.position.copy(latLonToVector3(vLat, vLon, R, 0.3))
        ringMesh1.lookAt(new THREE.Vector3(0, 0, 0))
        aisGroupRef.current.add(ringMesh1)

        const ringGeo2 = new THREE.RingGeometry(1.6, 2.0, 16)
        const ringMat2 = new THREE.MeshBasicMaterial({
          color,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.35,
        })
        const ringMesh2 = new THREE.Mesh(ringGeo2, ringMat2)
        ringMesh2.position.copy(latLonToVector3(vLat, vLon, R, 0.28))
        ringMesh2.lookAt(new THREE.Vector3(0, 0, 0))
        aisGroupRef.current.add(ringMesh2)
      })
    }
  }, [result, flyTo])

  // Synchronize layer group visibility with toggle states
  useEffect(() => {
    if (sarGroupRef.current) sarGroupRef.current.visible = Boolean(layers.sar_detection)
    if (temporalGroupRef.current) temporalGroupRef.current.visible = Boolean(layers.temporal_change)
    if (driftGroupRef.current) driftGroupRef.current.visible = Boolean(layers.drift_trajectory)
    if (originGroupRef.current) originGroupRef.current.visible = Boolean(layers.drift_origin)
    if (aisGroupRef.current) aisGroupRef.current.visible = Boolean(layers.ais_tracks)
    if (fusionGroupRef.current) fusionGroupRef.current.visible = Boolean(layers.fused_evidence)
    if (aoiGroupRef.current) aoiGroupRef.current.visible = layers.aoi_geometry !== false
    if (footprintGroupRef.current) footprintGroupRef.current.visible = layers.observation_footprint !== false
  }, [layers])

  // Clear & Rebuild Phase 7C AOI & Observation Footprint Layers
  useEffect(() => {
    const clearGroup = (group: THREE.Group) => {
      while (group.children.length > 0) {
        const obj = group.children[0]
        group.remove(obj)
      }
    }

    clearGroup(aoiGroupRef.current)
    clearGroup(footprintGroupRef.current)

    const effectiveAoi = aoiGeometry || investigation?.request?.aoi_bounding_box
    const effectiveFootprint = observationFootprint || investigation?.observation_footprint

    const R = 100

    // Render AOI Geometry (User Input / Operator Parameter)
    if (effectiveAoi) {
      let aoiRings: [number, number][][] = []
      if (Array.isArray(effectiveAoi) && effectiveAoi.length === 4) {
        // [min_lon, min_lat, max_lon, max_lat]
        const [minLon, minLat, maxLon, maxLat] = effectiveAoi
        aoiRings = [[
          [minLon, minLat],
          [maxLon, minLat],
          [maxLon, maxLat],
          [minLon, maxLat],
          [minLon, minLat],
        ]]
      } else if (effectiveAoi.coordinates) {
        aoiRings = effectiveAoi.type === 'Polygon' ? effectiveAoi.coordinates : effectiveAoi.coordinates[0]
      }

      aoiRings.forEach((ring) => {
        if (!Array.isArray(ring) || ring.length < 3) return
        const points = ring.map(([lon, lat]: [number, number]) => latLonToVector3(lat, lon, R, 0.28))
        const lineGeo = new THREE.BufferGeometry().setFromPoints(points)
        const lineMat = new THREE.LineBasicMaterial({
          color: 0x00f2fe, // Cyan for operator AOI input
          linewidth: 2,
        })
        const lineLoop = new THREE.LineLoop(lineGeo, lineMat)
        const centerLat = ring.reduce((sum, p) => sum + p[1], 0) / ring.length
        const centerLon = ring.reduce((sum, p) => sum + p[0], 0) / ring.length

        lineLoop.userData = {
          evidenceId: 'USER_AOI',
          label: `AOI: ${investigation?.request?.aoi_name || 'Operator Selected AOI'} (USER_INPUT)`,
          lat: centerLat,
          lon: centerLon,
          isUserInput: true,
        }
        aoiGroupRef.current.add(lineLoop)
        interactiveObjectsRef.current.push(lineLoop)

        // Subtle corner markers
        ring.slice(0, 4).forEach(([lon, lat]: [number, number]) => {
          const cornerGeo = new THREE.SphereGeometry(0.5, 8, 8)
          const cornerMat = new THREE.MeshBasicMaterial({ color: 0x00f2fe })
          const cornerMesh = new THREE.Mesh(cornerGeo, cornerMat)
          cornerMesh.position.copy(latLonToVector3(lat, lon, R, 0.3))
          cornerMesh.userData = lineLoop.userData
          aoiGroupRef.current.add(cornerMesh)
          interactiveObjectsRef.current.push(cornerMesh)
        })

        if (!result) {
          flyTo(centerLat, centerLon, 135)
        }
      })
    }

    // Render Observation Footprint (Real Sentinel-1 SAR Evidence)
    if (effectiveFootprint) {
      let footprintRings: [number, number][][] = []
      if (effectiveFootprint.coordinates) {
        footprintRings = effectiveFootprint.type === 'Polygon' ? effectiveFootprint.coordinates : effectiveFootprint.coordinates[0]
      } else if (Array.isArray(effectiveFootprint) && Array.isArray(effectiveFootprint[0])) {
        footprintRings = [effectiveFootprint]
      }

      footprintRings.forEach((ring) => {
        if (!Array.isArray(ring) || ring.length < 3) return
        const points = ring.map(([lon, lat]: [number, number]) => latLonToVector3(lat, lon, R, 0.22))
        const lineGeo = new THREE.BufferGeometry().setFromPoints(points)
        const lineMat = new THREE.LineBasicMaterial({
          color: 0x10b981, // Emerald for authentic repository observation
          linewidth: 2,
        })
        const lineLoop = new THREE.LineLoop(lineGeo, lineMat)
        const centerLat = ring.reduce((sum, p) => sum + p[1], 0) / ring.length
        const centerLon = ring.reduce((sum, p) => sum + p[0], 0) / ring.length

        lineLoop.userData = {
          evidenceId: 'OBSERVATION_FOOTPRINT',
          label: `Sentinel-1 Observation Footprint (REAL_REPOSITORY_EVIDENCE)`,
          lat: centerLat,
          lon: centerLon,
        }
        footprintGroupRef.current.add(lineLoop)
        interactiveObjectsRef.current.push(lineLoop)

        if (!result && !effectiveAoi) {
          flyTo(centerLat, centerLon, 135)
        }
      })
    }
  }, [investigation, aoiGeometry, observationFootprint, flyTo, result])

  // Focus camera when selectedEvidenceId changes
  useEffect(() => {
    if (!selectedEvidenceId || isQuarantined) return
    const match = interactiveObjectsRef.current.find(
      (obj) => obj.userData?.evidenceId === selectedEvidenceId
    )
    if (match?.userData?.lat && match?.userData?.lon) {
      flyTo(match.userData.lat, match.userData.lon, 130)
    }
  }, [selectedEvidenceId, flyTo, isQuarantined])

  return (
    <div className="center-viewport">
      <div className="globe-canvas-wrapper" ref={containerRef}>
        {/* Loading Overlay */}
        {isLoading && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(5, 8, 17, 0.75)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 50,
              gap: '12px',
            }}
          >
            <div className="spinner" />
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--cyan-primary)' }}>
              SYNCHRONIZING GEOSPATIAL DATA...
            </div>
          </div>
        )}

        {/* Empty Result Overlay */}
        {!isLoading && !result && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              textAlign: 'center',
              background: 'rgba(10, 16, 30, 0.85)',
              padding: '24px 32px',
              borderRadius: '12px',
              border: '1px solid var(--border-subtle)',
              backdropFilter: 'var(--glass-blur)',
              zIndex: 40,
              maxWidth: '380px',
            }}
          >
            <Info size={28} style={{ color: 'var(--cyan-primary)', marginBottom: '8px' }} />
            <h3 style={{ fontSize: '14px', marginBottom: '6px' }}>NO ACTIVE JOB LOADED</h3>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Launch <strong>RUN DEMO_FUSION</strong> or <strong>RUN ARTIFACT_FUSION</strong> from the control panel to display 3D satellite evidence, drift trajectories, and candidate vessel tracks.
            </p>
          </div>
        )}

        {/* Top-Left Coordinates HUD */}
        <div className="globe-hud-top">
          <div className="hud-pill">
            <Compass size={13} />
            <span>
              LAT: {hudCoords.lat >= 0 ? `${hudCoords.lat.toFixed(4)}° N` : `${Math.abs(hudCoords.lat).toFixed(4)}° S`}{' '}
              | LON: {hudCoords.lon >= 0 ? `${hudCoords.lon.toFixed(4)}° E` : `${Math.abs(hudCoords.lon).toFixed(4)}° W`}
            </span>
          </div>

          <div className="hud-pill">
            <span>ALT: {cameraAltitudeKm} km</span>
          </div>

          <div
            className="hud-pill"
            style={{
              borderColor: 'rgba(245, 158, 11, 0.3)',
              color: 'var(--amber-secondary)',
            }}
          >
            <span>Vector Basemap (Fail-Closed: No Fabricated Satellite Imagery)</span>
          </div>
        </div>

        {/* Central Viewport Event Focus HUD Banner (when job result exists) */}
        {result && (
          <div
            className="globe-event-focus-hud"
            style={{
              position: 'absolute',
              top: '58px',
              left: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '6px 12px',
              background: 'rgba(9, 14, 26, 0.88)',
              border: '1px solid rgba(0, 242, 254, 0.35)',
              borderRadius: '8px',
              backdropFilter: 'var(--glass-blur)',
              zIndex: 25,
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.4)',
            }}
          >
            <Crosshair size={13} style={{ color: 'var(--cyan-primary)' }} />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                {result.mode === 'REAL_REPOSITORY'
                  ? `REAL INVESTIGATION: ${result.scenario_metadata?.label || result.scenario_id || 'TRUJILLO_00007_01339'}`
                  : 'INCIDENT AUTO-FOCUS: EASTERN MEDITERRANEAN'}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                {result.total_evidence_items} Evidence Ledger Items | {result.plausible_candidate_count} Plausible Vessel Hypotheses
                {result.mode === 'REAL_REPOSITORY' && (
                  result.has_synthetic_dependencies || result.provenance_status === 'PROVENANCE_LIMITED'
                    ? ' | PROVENANCE: LIMITED (SYNTHETIC DEPENDENCIES)'
                    : ` | PROVENANCE: ${result.provenance_class || 'HISTORICAL_ARCHIVE'}`
                )}
              </span>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: '3px 8px', fontSize: '10px', marginLeft: '6px' }}
              onClick={() => {
                const cLat = result.scenario_metadata?.centroid ? result.scenario_metadata.centroid[1] : 32.18
                const cLon = result.scenario_metadata?.centroid ? result.scenario_metadata.centroid[0] : 30.65
                flyTo(cLat, cLon, 135)
              }}
              title="Recenter Camera on Primary Incident Scene"
            >
              Recenter Event
            </button>
          </div>
        )}

        {/* Selected Location HUD Overlay (when user clicks on globe) */}
        {selectedLocation && (
          <div
            className="globe-user-location-hud"
            style={{
              position: 'absolute',
              bottom: '16px',
              left: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '8px 14px',
              background: 'rgba(15, 23, 42, 0.92)',
              border: '1px solid var(--cyan-primary)',
              borderRadius: '8px',
              boxShadow: '0 0 16px rgba(0, 242, 254, 0.3)',
              zIndex: 35,
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <Target size={16} style={{ color: 'var(--cyan-primary)', flexShrink: 0 }} />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#ffffff', fontWeight: 600 }}>
                  SELECTED LOCATION: {selectedLocation.lat >= 0 ? `${selectedLocation.lat.toFixed(4)}° N` : `${Math.abs(selectedLocation.lat).toFixed(4)}° S`}, {selectedLocation.lon >= 0 ? `${selectedLocation.lon.toFixed(4)}° E` : `${Math.abs(selectedLocation.lon).toFixed(4)}° W`}
                </span>
                <span
                  className="badge"
                  style={{
                    fontSize: '9px',
                    padding: '1px 5px',
                    background: 'rgba(0, 242, 254, 0.15)',
                    color: 'var(--cyan-primary)',
                    border: '1px solid rgba(0, 242, 254, 0.3)',
                  }}
                >
                  OPERATOR REFERENCE — NOT EVIDENCE
                </span>
              </div>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                User-selected coordinate. Does not create scientific evidence or alter drift trajectories.
              </span>
            </div>

            <div style={{ display: 'flex', gap: '6px', marginLeft: '6px' }}>
              <button
                type="button"
                className="btn btn-primary"
                style={{ padding: '3px 8px', fontSize: '10px' }}
                onClick={() => flyTo(selectedLocation.lat, selectedLocation.lon, 130)}
                title="Fly Camera to Selected Location"
              >
                Focus
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '3px 8px', fontSize: '10px' }}
                onClick={() => onSelectLocation(null)}
                title="Clear Location Selection"
              >
                <X size={12} />
              </button>
            </div>
          </div>
        )}

        {/* Hovered Feature Tooltip */}
        {hoveredFeature && !selectedLocation && (
          <div
            style={{
              position: 'absolute',
              bottom: '16px',
              left: '16px',
              padding: '8px 14px',
              background: 'rgba(9, 14, 26, 0.9)',
              border: '1px solid var(--cyan-primary)',
              borderRadius: '6px',
              boxShadow: '0 0 12px rgba(0, 242, 254, 0.3)',
              zIndex: 35,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <MapPin size={14} style={{ color: 'var(--cyan-primary)' }} />
            <span>{hoveredFeature.name}</span>
          </div>
        )}

        {/* Evidence Quarantine Watermark */}
        {isQuarantined && (
          <div
            style={{
              position: 'absolute',
              top: '16px',
              left: '50%',
              transform: 'translateX(-50%)',
              padding: '6px 14px',
              background: 'rgba(239, 68, 68, 0.9)',
              border: '1px solid #f87171',
              borderRadius: '6px',
              color: '#ffffff',
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.6px',
              zIndex: 40,
              pointerEvents: 'none',
              boxShadow: '0 0 16px rgba(239, 68, 68, 0.6)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
            data-testid="globe-quarantine-watermark"
          >
            <ShieldAlert size={14} />
            <span>CACHED EVIDENCE QUARANTINED — CURRENT CONTEXT MISMATCH</span>
          </div>
        )}

        {/* Top-Right Camera Controls Overlay */}
        <div className="globe-controls-overlay">
          <button
            type="button"
            className="icon-button"
            onClick={() => {
              if (cameraRef.current) {
                cameraRef.current.position.multiplyScalar(0.8)
                controlsRef.current?.update()
              }
            }}
            title="Zoom In"
          >
            <Maximize2 size={14} />
          </button>

          <button
            type="button"
            className="icon-button"
            onClick={() => {
              if (cameraRef.current) {
                cameraRef.current.position.multiplyScalar(1.25)
                controlsRef.current?.update()
              }
            }}
            title="Zoom Out"
          >
            <Minimize2 size={14} />
          </button>

          <button
            type="button"
            className="icon-button"
            onClick={() => {
              const cLat = result?.scenario_metadata?.centroid ? result.scenario_metadata.centroid[1] : 32.18
              const cLon = result?.scenario_metadata?.centroid ? result.scenario_metadata.centroid[0] : 30.65
              flyTo(cLat, cLon, 135)
            }}
            title="Focus Detection Zone"
          >
            <LocateFixed size={14} />
          </button>

          <button
            type="button"
            className="icon-button"
            onClick={() => {
              if (cameraRef.current && controlsRef.current) {
                cameraRef.current.position.set(0, 70, 240)
                controlsRef.current.target.set(0, 0, 0)
                controlsRef.current.update()
              }
            }}
            title="Reset to Global View"
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
