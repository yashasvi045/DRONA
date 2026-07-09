// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title DroneRegistry
 * @notice Registers drones and logs their passage through mesh nodes.
 */
contract DroneRegistry is Ownable {

    // ─── Structs ────────────────────────────────────────────────────────────

    struct Drone {
        string  droneId;      // unique human-readable ID (e.g. "DMT-001")
        address owner;        // wallet address of the drone operator
        bool    isActive;     // whether the drone is cleared to fly
        uint256 registeredAt;
    }

    struct PassageLog {
        string  droneId;
        string  nodeId;       // mesh node that recorded the passage
        int256  lat;          // latitude  × 1e6 (avoid floats on-chain)
        int256  lon;          // longitude × 1e6
        uint256 timestamp;
    }

    // ─── Constants ──────────────────────────────────────────────────────────

    // Cap on-chain log storage per drone to bound gas cost growth.
    // Older passages are still captured in emitted events (off-chain indexable).
    uint256 public constant MAX_LOGS_PER_DRONE = 500;

    // ─── State ──────────────────────────────────────────────────────────────

    mapping(string => Drone)         public drones;          // droneId -> Drone
    mapping(string => PassageLog[])  public passageLogs;     // droneId -> logs (capped)
    string[]                         public registeredDroneIds;

    // ─── Events ─────────────────────────────────────────────────────────────

    event DroneRegistered(string indexed droneId, address indexed owner, uint256 timestamp);
    event PassageLogged(string indexed droneId, string indexed nodeId, int256 lat, int256 lon, uint256 timestamp);
    event DroneStatusUpdated(string indexed droneId, bool isActive);

    // ─── Constructor ────────────────────────────────────────────────────────

    constructor() Ownable(msg.sender) {}

    // ─── Functions ──────────────────────────────────────────────────────────

    /**
     * @notice Register a new drone. Only the contract owner (authority) can do this.
     * @param droneId  Unique drone identifier string.
     * @param operator Wallet address of the drone's operator.
     */
    function registerDrone(string calldata droneId, address operator) external onlyOwner {
        require(bytes(droneId).length > 0, "DroneRegistry: empty droneId");
        require(operator != address(0), "DroneRegistry: zero address");
        require(bytes(drones[droneId].droneId).length == 0, "DroneRegistry: already registered");

        drones[droneId] = Drone({
            droneId:      droneId,
            owner:        operator,
            isActive:     true,
            registeredAt: block.timestamp
        });

        registeredDroneIds.push(droneId);
        emit DroneRegistered(droneId, operator, block.timestamp);
    }

    /**
     * @notice Log a drone's passage through a mesh node.
     * @param droneId Drone identifier.
     * @param nodeId  Mesh node identifier.
     * @param lat     Latitude  multiplied by 1e6 (e.g. 12.971599 → 12971599).
     * @param lon     Longitude multiplied by 1e6 (e.g. 77.594566 → 77594566).
     */
    function logPassage(
        string calldata droneId,
        string calldata nodeId,
        int256          lat,
        int256          lon
    ) external {
        Drone storage drone = drones[droneId];
        require(bytes(drone.droneId).length > 0, "DroneRegistry: drone not registered");
        require(drone.isActive, "DroneRegistry: drone is not active");

        // If the cap is reached, drop the oldest entry (shift left) to make room.
        // The PassageLogged event always fires, so no passage is ever lost off-chain.
        if (passageLogs[droneId].length >= MAX_LOGS_PER_DRONE) {
            for (uint256 i = 0; i < passageLogs[droneId].length - 1; i++) {
                passageLogs[droneId][i] = passageLogs[droneId][i + 1];
            }
            passageLogs[droneId].pop();
        }

        passageLogs[droneId].push(PassageLog({
            droneId:   droneId,
            nodeId:    nodeId,
            lat:       lat,
            lon:       lon,
            timestamp: block.timestamp
        }));

        emit PassageLogged(droneId, nodeId, lat, lon, block.timestamp);
    }

    /**
     * @notice Enable or disable a drone (compliance / grounding).
     */
    function setDroneStatus(string calldata droneId, bool active) external onlyOwner {
        require(bytes(drones[droneId].droneId).length > 0, "DroneRegistry: drone not registered");
        drones[droneId].isActive = active;
        emit DroneStatusUpdated(droneId, active);
    }

    /**
     * @notice Returns all passage logs for a given drone.
     */
    function getPassageLogs(string calldata droneId) external view returns (PassageLog[] memory) {
        return passageLogs[droneId];
    }

    /**
     * @notice Returns total number of registered drones.
     */
    function getDroneCount() external view returns (uint256) {
        return registeredDroneIds.length;
    }
}
