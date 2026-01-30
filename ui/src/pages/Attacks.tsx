import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  UserGroupIcon,
  BoltIcon,
  PlayCircleIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';
import { attacksApi } from '../api';
import { useTenantPath } from '../hooks/useTenantPath';

// ============================================================================
// Styled Components
// ============================================================================

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const PageHeader = styled.div``;

const PageTitle = styled.h1`
  font-size: 1.5rem;
  font-weight: 700;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const PageDescription = styled.p`
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 1.25rem;

  @media (min-width: 640px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (min-width: 1024px) {
    grid-template-columns: repeat(4, 1fr);
  }
`;

const StatCardContainer = styled(Link)`
  display: block;
  text-decoration: none;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;

  &:hover {
    border-color: ${variables.accentColorPositive};
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
  }
`;

const StatCardContent = styled.div`
  padding: 1.25rem;
`;

const StatCardTop = styled.div`
  display: flex;
  align-items: center;
`;

const StatIconContainer = styled.div`
  flex-shrink: 0;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background-color: rgba(239, 68, 68, 0.2);
`;

const StatIcon = styled.div`
  width: 1.5rem;
  height: 1.5rem;
  color: #ef4444;
`;

const StatTextContainer = styled.div`
  margin-left: 1.25rem;
  flex: 1;
`;

const StatLabel = styled.dt`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const StatValue = styled.dd`
  font-size: 1.5rem;
  font-weight: 600;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const StatDescription = styled.p`
  margin-top: 0.75rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const Card = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
`;

const CardHeader = styled.div`
  padding: 1rem 1.5rem;
  border-bottom: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const CardTitle = styled.h3`
  font-size: 1rem;
  font-weight: 600;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const CardBody = styled.div`
  padding: 1.5rem;
`;

const CardLink = styled(Link)`
  font-size: 0.875rem;
  color: ${variables.accentColorPositive};
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
`;

const QuickLinksGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;

  @media (min-width: 640px) {
    grid-template-columns: repeat(3, 1fr);
  }
`;

const QuickLinkCard = styled(Link)`
  display: flex;
  align-items: center;
  padding: 1rem;
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  text-decoration: none;
  transition: border-color 0.2s, background-color 0.2s;

  &:hover {
    border-color: ${variables.accentColorPositive};
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }
`;

interface QuickLinkIconProps {
  $color: string;
}

const QuickLinkIcon = styled.div<QuickLinkIconProps>`
  width: 2rem;
  height: 2rem;
  margin-right: 0.75rem;
  color: ${props => props.$color};
`;

const QuickLinkText = styled.div``;

const QuickLinkTitle = styled.h3`
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const QuickLinkDescription = styled.p`
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin: 0.25rem 0 0;
`;

const List = styled.div``;

const ListItem = styled.div`
  padding: 1rem 1.5rem;
  border-bottom: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  transition: background-color 0.2s;

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }

  &:last-child {
    border-bottom: none;
  }
`;

const ListItemContent = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const ListItemLeft = styled.div``;

const ListItemTitle = styled.h4`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const ListItemSubtitle = styled.p`
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin: 0.125rem 0 0;
`;

const ListItemRight = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

interface BadgeProps {
  $color: string;
  $bgColor: string;
}

const ThreatBadge = styled.span<BadgeProps>`
  display: inline-flex;
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 0.25rem;
  background-color: ${props => props.$bgColor};
  color: ${props => props.$color};
`;

const CountryText = styled.span`
  font-size: 0.75rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

// ============================================================================
// Helper Components
// ============================================================================

function StatCard({
  title,
  value,
  icon: Icon,
  href,
  description,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  href: string;
  description: string;
}) {
  return (
    <StatCardContainer to={href}>
      <StatCardContent>
        <StatCardTop>
          <StatIconContainer>
            <StatIcon as={Icon} />
          </StatIconContainer>
          <StatTextContainer>
            <dl>
              <StatLabel>{title}</StatLabel>
              <StatValue>{value}</StatValue>
            </dl>
          </StatTextContainer>
        </StatCardTop>
        <StatDescription>{description}</StatDescription>
      </StatCardContent>
    </StatCardContainer>
  );
}

function ThreatLevelBadge({ level }: { level: string }) {
  const colors: Record<string, { color: string; bgColor: string }> = {
    script_kiddie: { color: '#9ca3af', bgColor: 'rgba(156, 163, 175, 0.2)' },
    opportunistic: { color: '#eab308', bgColor: 'rgba(234, 179, 8, 0.2)' },
    organized_crime: { color: '#f97316', bgColor: 'rgba(249, 115, 22, 0.2)' },
    hacktivist: { color: '#a855f7', bgColor: 'rgba(168, 85, 247, 0.2)' },
    insider_threat: { color: '#ec4899', bgColor: 'rgba(236, 72, 153, 0.2)' },
    apt: { color: '#ef4444', bgColor: 'rgba(239, 68, 68, 0.2)' },
    nation_state: { color: '#dc2626', bgColor: 'rgba(220, 38, 38, 0.3)' },
  };

  const labels: Record<string, string> = {
    script_kiddie: 'Script Kiddie',
    opportunistic: 'Opportunistic',
    organized_crime: 'Organized Crime',
    hacktivist: 'Hacktivist',
    insider_threat: 'Insider',
    apt: 'APT',
    nation_state: 'Nation State',
  };

  const { color, bgColor } = colors[level] || { color: '#9ca3af', bgColor: 'rgba(156, 163, 175, 0.2)' };

  return (
    <ThreatBadge $color={color} $bgColor={bgColor}>
      {labels[level] || level}
    </ThreatBadge>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function Attacks() {
  const { toPath } = useTenantPath();

  const { data: threatActors = [] } = useQuery({
    queryKey: ['threat-actors'],
    queryFn: attacksApi.listThreatActors,
  });

  const { data: campaigns = [] } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => attacksApi.listCampaigns(),
  });

  const { data: scenarios = [] } = useQuery({
    queryKey: ['scenarios'],
    queryFn: attacksApi.listScenarios,
  });

  const activeCampaigns = campaigns.filter((c) => c.status === 'running').length;

  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>Attack Simulation</PageTitle>
        <PageDescription>
          Simulate adversarial attacks for security training and detection testing
        </PageDescription>
      </PageHeader>

      {/* Overview Cards */}
      <StatsGrid>
        <StatCard
          title="Threat Actors"
          value={threatActors.length}
          icon={UserGroupIcon}
          href={toPath('attacks/threat-actors')}
          description="From script kiddies to nation-state APTs"
        />
        <StatCard
          title="Active Campaigns"
          value={activeCampaigns}
          icon={BoltIcon}
          href={toPath('attacks/campaigns')}
          description="Currently running attack simulations"
        />
        <StatCard
          title="Total Campaigns"
          value={campaigns.length}
          icon={PlayCircleIcon}
          href={toPath('attacks/campaigns')}
          description="All attack campaigns"
        />
        <StatCard
          title="Scenarios"
          value={scenarios.length}
          icon={ShieldExclamationIcon}
          href={toPath('attacks/scenarios')}
          description="Pre-built attack scenarios"
        />
      </StatsGrid>

      {/* Quick Links */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Links</CardTitle>
        </CardHeader>
        <CardBody>
          <QuickLinksGrid>
            <QuickLinkCard to={toPath('attacks/threat-actors')}>
              <QuickLinkIcon $color="#ef4444">
                <UserGroupIcon />
              </QuickLinkIcon>
              <QuickLinkText>
                <QuickLinkTitle>Threat Actors</QuickLinkTitle>
                <QuickLinkDescription>Browse adversary profiles</QuickLinkDescription>
              </QuickLinkText>
            </QuickLinkCard>
            <QuickLinkCard to={toPath('attacks/campaigns')}>
              <QuickLinkIcon $color="#eab308">
                <BoltIcon />
              </QuickLinkIcon>
              <QuickLinkText>
                <QuickLinkTitle>Campaigns</QuickLinkTitle>
                <QuickLinkDescription>View active attacks</QuickLinkDescription>
              </QuickLinkText>
            </QuickLinkCard>
            <QuickLinkCard to={toPath('attacks/scenarios')}>
              <QuickLinkIcon $color="#a855f7">
                <ShieldExclamationIcon />
              </QuickLinkIcon>
              <QuickLinkText>
                <QuickLinkTitle>Scenarios</QuickLinkTitle>
                <QuickLinkDescription>Run pre-built attacks</QuickLinkDescription>
              </QuickLinkText>
            </QuickLinkCard>
          </QuickLinksGrid>
        </CardBody>
      </Card>

      {/* Featured Threat Actors */}
      <Card>
        <CardHeader>
          <CardTitle>Featured Threat Actors</CardTitle>
          <CardLink to={toPath('attacks/threat-actors')}>View all</CardLink>
        </CardHeader>
        <List>
          {threatActors.slice(0, 5).map((actor) => (
            <ListItem key={actor.id}>
              <ListItemContent>
                <ListItemLeft>
                  <ListItemTitle>{actor.name}</ListItemTitle>
                  <ListItemSubtitle>
                    {actor.aliases.slice(0, 3).join(', ')}
                    {actor.aliases.length > 3 && ` +${actor.aliases.length - 3} more`}
                  </ListItemSubtitle>
                </ListItemLeft>
                <ListItemRight>
                  <ThreatLevelBadge level={actor.threat_level} />
                  {actor.attributed_country && (
                    <CountryText>{actor.attributed_country}</CountryText>
                  )}
                </ListItemRight>
              </ListItemContent>
            </ListItem>
          ))}
        </List>
      </Card>
    </PageContainer>
  );
}
