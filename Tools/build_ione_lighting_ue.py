"""Build editable UI-domain materials for Ione's authored 2D scene layers."""
import unreal

E = unreal.MaterialEditingLibrary
PATH = '/Game/UI/Materials'
tools = unreal.AssetToolsHelpers.get_asset_tools()

PORTRAIT = r'''
float4 p = Texture2DSample(Portrait, PortraitSampler, UV);
float2 face = float2(.505, .133);
float cheek = exp(-dot((UV-float2(.555,.139))/float2(.052,.052),(UV-float2(.555,.139))/float2(.052,.052)));
float jaw = exp(-dot((UV-float2(.485,.173))/float2(.08,.019),(UV-float2(.485,.173))/float2(.08,.019)));
float faceShade = exp(-dot((UV-float2(.46,.145))/float2(.048,.05),(UV-float2(.46,.145))/float2(.048,.05)));
float leftCoat = exp(-dot((UV-float2(.32,.44))/float2(.12,.23),(UV-float2(.32,.44))/float2(.12,.23)));
float rightCoat = exp(-dot((UV-float2(.67,.48))/float2(.15,.25),(UV-float2(.67,.48))/float2(.15,.25)));
float nose = exp(-dot((UV-float2(.515,.143))/float2(.012,.022),(UV-float2(.515,.143))/float2(.012,.022)));
float sleeveY = PoseIndex < .5 ? .25 : PoseIndex < 1.5 ? .32 : PoseIndex < 2.5 ? .23 : .31;
float sleeveX = PoseIndex < .5 ? .71 : PoseIndex < 1.5 ? .83 : PoseIndex < 2.5 ? .70 : .65;
float sleeve = exp(-dot((UV-float2(sleeveX,sleeveY))/float2(.12,.08),(UV-float2(sleeveX,sleeveY))/float2(.12,.08)));
float leg = exp(-dot((UV-float2(.64,.83))/float2(.12,.16),(UV-float2(.64,.83))/float2(.12,.16)));
float edgeA = Texture2DSample(Portrait,PortraitSampler,UV-float2(.006,0)).a;
float rim = saturate(p.a-edgeA)*smoothstep(.8,.1,UV.y);
float facePlane=exp(-dot((UV-float2(.50,.14))/float2(.12,.07),(UV-float2(.50,.14))/float2(.12,.07)))*(1-smoothstep(.49,.515,UV.x));
float shade = max(.14,.57 - .24*leftCoat - .15*jaw - .23*facePlane);
float warm = (.26*cheek+.07*nose+.21*rightCoat+.16*sleeve+.13*leg)*Lamp;
float3 shadowHue = lerp(float3(.73,.80,.84),float3(1,1,1),saturate(warm*3));
float3 color = p.rgb*shade*shadowHue + p.rgb*float3(1.0,.63,.31)*warm;
float warmEdge=saturate(p.a-Texture2DSample(Portrait,PortraitSampler,UV+float2(.007,0)).a);
float hairEdge=(1-smoothstep(.17,.25,UV.y))*smoothstep(.24,.58,dot(p.rgb,float3(.2126,.7152,.0722)));
float upperEdge=1-smoothstep(.30,.5,UV.y);
color += float3(.62,.29,.065)*warmEdge*(hairEdge+.12*upperEdge)*Lamp;
return float4(saturate(color),p.a);
'''

SHADOW = r'''
float a=0;
for(int x=-2;x<=2;x++)for(int y=-2;y<=2;y++)
 a+=Texture2DSample(Portrait,PortraitSampler,UV+float2(x*.006,y*.004)).a/25.;
return float4(.018,.024,.025,a*.22*Lamp);
'''

DIALOGUE = r'''
float topEdge=1-step(.0042,UV.y);
return float4(lerp(float3(.0052,.0097,.011),float3(.38,.22,.105),topEdge),lerp(.94,1,topEdge));
'''

BACKGROUND = r'''
float4 p=Texture2DSample(Portrait,PortraitSampler,UV);
float luma=dot(p.rgb,float3(.2126,.7152,.0722));
float3 desat=lerp(luma.xxx,p.rgb,.62);
float floorShade=smoothstep(.45,1,UV.y);
return float4(desat*float3(.38,.39,.40)*(1-.48*floorShade),1);
'''

GLOW = r'''
float2 q=(UV-float2(.5,.42))*float2(1,1.15);
float halo=exp(-dot(q,q)*18);
float desk=exp(-dot((UV-float2(.5,.78))*float2(1.2,5),(UV-float2(.5,.78))*float2(1.2,5))*9);
float coneWidth=.06+max(0,UV.y-.42)*.45;
float cone=(1-smoothstep(coneWidth,coneWidth+.05,abs(UV.x-.5)))*smoothstep(.40,.47,UV.y)*(1-smoothstep(.8,1,UV.y));
float dust=0;
for(int i=0;i<8;i++){
 float2 center=float2(.22+frac(sin(i*17.31)*437.2)*.56,.43+frac(sin(i*9.2)*214.3+Phase*.008)*.52);
 float2 d=(UV-center)*float2(1,1.2);dust+=exp(-dot(d,d)*160000)*cone;
}
return float4(.90,.38,.10,saturate((halo*.075+desk*.055+cone*.018+dust*.14)*Lamp));
'''

for name, code, textured in [('M_IonePortraitLight_UI',PORTRAIT,True),
                              ('M_IoneBackground_UI',BACKGROUND,True),
                              ('M_IoneBackShadow_UI',SHADOW,True),
                              ('M_IoneDialogue_UI',DIALOGUE,False),
                              ('M_IoneLampGlow_UI',GLOW,False)]:
    mat = unreal.load_asset(PATH+'/'+name)
    if mat is None:
        mat = tools.create_asset(name,PATH,unreal.Material,unreal.MaterialFactoryNew())
    else:
        E.delete_all_material_expressions(mat)
    mat.set_editor_property('material_domain',unreal.MaterialDomain.MD_UI)
    mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    custom = E.create_material_expression(mat,unreal.MaterialExpressionCustom)
    custom.set_editor_property('code',code)
    custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    names=['UV','Lamp','PoseIndex','Phase']+(['Portrait'] if textured else [])
    inputs=[]
    for n in names:
        item=unreal.CustomInput()
        item.set_editor_property('input_name',n)
        inputs.append(item)
    custom.set_editor_property('inputs',inputs)
    uv=E.create_material_expression(mat,unreal.MaterialExpressionTextureCoordinate)
    assert E.connect_material_expressions(uv,'',custom,'UV')
    for parameter,default in [('Lamp',1.0),('PoseIndex',0.0),('Phase',0.0)]:
        node=E.create_material_expression(mat,unreal.MaterialExpressionScalarParameter)
        node.set_editor_property('parameter_name',parameter)
        node.set_editor_property('default_value',default)
        assert E.connect_material_expressions(node,'',custom,parameter)
    if textured:
        tex=E.create_material_expression(mat,unreal.MaterialExpressionTextureObjectParameter)
        tex.set_editor_property('parameter_name','Portrait')
        tex.set_editor_property('texture',unreal.load_asset('/Game/UI/Ione_ArchiveRoom_Background_v2' if name=='M_IoneBackground_UI' else '/Game/Character/Performance2D/Ione_Listen_Front'))
        assert E.connect_material_expressions(tex,'',custom,'Portrait')
    for alpha,prop in [(False,unreal.MaterialProperty.MP_EMISSIVE_COLOR),(True,unreal.MaterialProperty.MP_OPACITY)]:
        mask=E.create_material_expression(mat,unreal.MaterialExpressionComponentMask)
        for ch in ['r','g','b']: mask.set_editor_property(ch,not alpha)
        mask.set_editor_property('a',alpha)
        assert E.connect_material_expressions(custom,'',mask,'')
        assert E.connect_material_property(mask,'',prop)
    E.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    unreal.log('Ione UI material saved: '+name)
