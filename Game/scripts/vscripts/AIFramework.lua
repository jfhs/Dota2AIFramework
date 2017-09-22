--[[
	AI Competition framework.

	This is the main class of the Dota 2 AI competition framework developed for the purpose of holding
	AI competitions where AI players are presented with tasks in Dota 2 to accomplish as well as possible
	without a human intervening.

	Code: Perry
	Date: October, 2015
]]

--Include AI
require( 'AI.AIManager' )

--Require game mode logic
require( 'AIGameModes.BaseAIGameMode' )

--Class definition
if AIFramework == nil then
	AIFramework = class({})
end

--Initialisation
function AIFramework:Init()
	print( 'Initialising AI framework.' )

	--Make table to store vision dummies in
	AIFramework.visionDummies = {}

	--GameRules:FinishCustomGameSetup()
	GameRules:SetCustomGameTeamMaxPlayers( 1, 	5 )

	Convars:SetInt( 'dota_auto_surrender_all_disconnected_timeout', 7200 )
	SendToServerConsole( 'customgamesetup_set_auto_launch_delay 30' )
	GameRules:SetShowcaseTime(0)
	GameRules:SetStrategyTime(10)
	GameRules:SetHeroSelectionTime(0)
--	GameRules:SetCustomGameSetupTimeout(0)

	--Initialise the AI manager
	AIManager:Init()

	--Register event listeners
	ListenToGameEvent( 'player_connect_full', Dynamic_Wrap( AIFramework, 'OnPlayerConnect' ), self )
	ListenToGameEvent( 'game_rules_state_change', Dynamic_Wrap( AIFramework, 'OnGameStateChange' ), self )
	CustomGameEventManager:RegisterListener( 'spawn_ai', function(...) self:SpawnAI(...) end )

	--Read in gamemode config
	self.config = LoadKeyValues("scripts/config/gamemode_ai.kv")
	--Send gamemode info to nettable for UI
	local nettable = {}
	for _, gamemode in pairs(self.config) do
		table.insert(nettable, {name = gamemode.Name, name, AI = gamemode.AI})
	end
	CustomNetTables:SetTableValue("config", "gamemodes", nettable)
end

--player_connect_full event handler
function AIFramework:OnPlayerConnect( event )
	PlayerResource:SetCustomTeamAssignment( event.index, 1 )

	AIManager.numPlayers = AIManager.numPlayers + 1
end

--game_rules_state_changed event handler
function AIFramework:OnGameStateChange( event )
	local state = GameRules:State_Get()
	if state == DOTA_GAMERULES_STATE_CUSTOM_GAME_SETUP then
		self:SpawnAI("", {
			game_mode="1",
			ai1="2",
			ai2="0",
		})
		Timers:CreateTimer(20, function()
			-- Lock the team selection so that no more team changes can be made
--			Game.SetTeamSelectionLocked( true );
			GameRules:LockCustomGameSetupTeamAssignment(true)

			-- Disable the auto start count down
--			Game.SetAutoLaunchEnabled( false );
			GameRules:EnableCustomGameSetupAutoLaunch(false)

			-- Set the remaining time before the game starts
--			Game.SetRemainingSetupTime( 4 );
			GameRules:SetCustomGameSetupRemainingTime(4)
			--SendToServerConsole("customgamesetup_set_remaining_time 0")
			return nil
		end)
	end
	if state == DOTA_GAMERULES_STATE_PRE_GAME then
		self:OnGameLoaded()
	end
end

--Called once the game gets to the PRE_GAME state
function AIFramework:OnGameLoaded()
	local t = 1
	Timers:CreateTimer( 1, function()
		if t < 4 or not AIManager:IsReadyToStart() then
			--Count down
			ShowCenterMessage( 4 - t, 1 )
			print("Counting to " .. t)
		else
			ShowCenterMessage( 'Start!', 2 )
			--Initialise Radiant AI
			AIManager:InitAllAI( self.gameMode )

			--Initialise gamemode
			self.gameMode:OnGameStart( AIManager:GetAllHeroes() )

			return nil
		end

		t = t + 1
		return 1
	end)
end

function AIFramework:SpawnAI( source, args )
	--Load gamemode
	local modeConfig = self.config[args.game_mode]
	local gameMode = require( 'AIGameModes.'..modeConfig.Path )

	--Set up the game mode
	gameMode:Setup()

	--Load ai for the gamemode
	local heroes = {}
	if gameMode.FixedHeroes then
		heroes = gameMode.Heroes
	end

	--Load in AI
	if args.ai1 ~= "0" and args.ai1 ~= 0 then
		AIManager:AddAI( modeConfig.AI[args.ai1], DOTA_TEAM_GOODGUYS, heroes )
	end
	if args.ai2 ~= "0" and args.ai2 ~= 0 then
		AIManager:AddAI( modeConfig.AI[args.ai2], DOTA_TEAM_BADGUYS, heroes )
	end

	--Save gamemode for later
	self.gameMode = gameMode
end

--Show a center message for some duration
function ShowCenterMessage( msg, dur )
	local centerMessage = {
		message = msg,
		duration = dur or 3
	}
	FireGameEvent( "show_center_message", centerMessage )
end
