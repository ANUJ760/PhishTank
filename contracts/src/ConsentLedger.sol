// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

contract ConsentLedger {
    address public immutable coordinator;
    mapping(bytes32 => address) public ruleOwner;
    mapping(bytes32 => mapping(bytes32 => bool)) public approved;
    mapping(bytes32 => bool) public anchored;

    event RuleRegistered(bytes32 indexed ruleHash, address indexed owner);
    event RelaxationApproved(bytes32 indexed ruleHash, bytes32 indexed optionHash, address indexed owner);
    event ScheduleAnchored(bytes32 indexed scheduleHash, uint256 version, address indexed by);

    constructor() { coordinator = msg.sender; }

    function registerRule(bytes32 ruleHash, address owner) external {
        require(msg.sender == coordinator, "only coordinator");
        require(owner != address(0), "zero owner");
        require(ruleOwner[ruleHash] == address(0), "already registered");
        ruleOwner[ruleHash] = owner;
        emit RuleRegistered(ruleHash, owner);
    }

    function approveRelaxation(bytes32 ruleHash, bytes32 optionHash) external {
        require(ruleOwner[ruleHash] == msg.sender, "not rule owner");
        require(!approved[ruleHash][optionHash], "already approved");
        approved[ruleHash][optionHash] = true;
        emit RelaxationApproved(ruleHash, optionHash, msg.sender);
    }

    function anchorSchedule(bytes32 scheduleHash, uint256 version) external {
        require(msg.sender == coordinator, "only coordinator");
        require(!anchored[scheduleHash], "already anchored");
        anchored[scheduleHash] = true;
        emit ScheduleAnchored(scheduleHash, version, msg.sender);
    }
}
