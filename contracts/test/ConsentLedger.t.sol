// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import "forge-std/Test.sol";
import "../src/ConsentLedger.sol";

contract ConsentLedgerTest is Test {
    ConsentLedger ledger;
    address rao = address(0xA1);
    address eve = address(0xB2);
    bytes32 ruleHash = keccak256("rule1");
    bytes32 optionHash = keccak256("option1");

    function setUp() public { ledger = new ConsentLedger(); }
    function test_ownerCanApprove() public {
        ledger.registerRule(ruleHash, rao);
        vm.prank(rao); ledger.approveRelaxation(ruleHash, optionHash);
        assertTrue(ledger.approved(ruleHash, optionHash));
    }
    function test_nonOwnerReverts() public {
        ledger.registerRule(ruleHash, rao); vm.prank(eve);
        vm.expectRevert(bytes("not rule owner")); ledger.approveRelaxation(ruleHash, optionHash);
    }
    function test_onlyCoordinatorRegisters() public {
        vm.prank(eve); vm.expectRevert(bytes("only coordinator")); ledger.registerRule(ruleHash, rao);
    }
    function test_doubleRegisterReverts() public {
        ledger.registerRule(ruleHash, rao); vm.expectRevert(bytes("already registered")); ledger.registerRule(ruleHash, rao);
    }
    function test_anchorOnce() public {
        ledger.anchorSchedule(ruleHash, 1); assertTrue(ledger.anchored(ruleHash));
        vm.expectRevert(bytes("already anchored")); ledger.anchorSchedule(ruleHash, 1);
    }
}
