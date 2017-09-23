--[[
	Sample AI

	Sample AI to demonstrate and test the AI competition framework.

	Code: Perry
	Date: October, 2015
]]
require('json_helpers')
require('hero_tools')

--Define AI object
local AI = {}

--Initialisation function, called by the framework with parameters
function AI:Init( params )
	AI_Log( 'Sample AI: Hello world!' )

	--Save team
	self.team = params.team
	self.hero = params.heroes[1]
	self.data = params.data
	self.baseURL = 'http://localhost:8080/Dota2AIService/api/service/'

	--Start thinker
	Timers:CreateTimer( function()
		return self:Think()
	end)

	self.state = 0

--	AIUnitTests:Run( _G, self.hero, self.hero:GetAbilityByIndex( 0 ), AIPlayerResource )
end

function AI:Request(pathUri, data, callback)
	local fullURL = self.baseURL .. pathUri
	-- print("Trying to make request to " .. fullURL)
	local request = CreateHTTPRequestScriptVM("POST", fullURL)
	request:SetHTTPRequestHeaderValue("Accept", "application/json")
	request:SetHTTPRequestHeaderValue("X-Jersey-Tracing-Threshold", "VERBOSE")
	if data ~= nil then
		request:SetHTTPRequestRawPostBody('application/json', data)
	else
		request:SetHTTPRequestHeaderValue("Content-Length", "0")
	end
	request:Send(function(result)
		if result["StatusCode"] == 200 then
			local command = dkjson.decode(result['Body'])
			callback(command)
		else
			AI_Log("Dota2AI error sending request to :" .. fullURL)
			for k, v in pairs(result) do
				AI_Log(string.format("%s : %s\n", k, v))
			end
		end
	end)
end

--AI think function
function AI:Think()
	AI:Request('update', Dota2AI:JSONWorld(self.hero), function(command)
		Dota2AIBot:ParseHeroCommand(self.hero, command)
	end)

	return 1

	--Check if we're at the move target yet
--	AI_ExecuteOrderFromTable({
--		UnitIndex = self.hero:GetEntityIndex(),
--		OrderType = DOTA_UNIT_ORDER_ATTACK_MOVE,
--		Position = Vector( -2500, 1000, 0 )
--	})
--
--	return 2
end

--Return the AI object <-- IMPORTANT
return AI