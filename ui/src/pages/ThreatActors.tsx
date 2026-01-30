import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import styled from 'styled-components';
import { variables, pick } from '@splunk/themes';
import {
  UserGroupIcon,
  MagnifyingGlassIcon,
  GlobeAltIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { attacksApi } from '../api';
import { useTenantPath } from '../hooks/useTenantPath';
import type { ThreatActor } from '../types';

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

const FilterCard = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  padding: 1rem;
`;

const FilterRow = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;

  @media (min-width: 640px) {
    flex-direction: row;
  }
`;

const SearchContainer = styled.div`
  flex: 1;
  position: relative;
`;

const SearchIcon = styled.div`
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};

  svg {
    width: 1.25rem;
    height: 1.25rem;
  }
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 0.5rem 0.75rem 0.5rem 2.5rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.375rem;

  &:focus {
    outline: none;
    border-color: ${variables.accentColorPositive};
  }

  &::placeholder {
    color: ${pick({
      prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
    })};
  }
`;

const Select = styled.select`
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.375rem;
  min-width: 12rem;

  &:focus {
    outline: none;
    border-color: ${variables.accentColorPositive};
  }
`;

const ResultsCount = styled.div`
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;

  @media (min-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (min-width: 1024px) {
    grid-template-columns: repeat(3, 1fr);
  }
`;

const Card = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  overflow: hidden;
  transition: border-color 0.2s;

  &:hover {
    border-color: ${variables.accentColorPositive};
  }
`;

const CardContent = styled.div`
  padding: 1.25rem;
`;

const CardHeader = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
`;

const CardHeaderLeft = styled.div`
  display: flex;
  align-items: center;
`;

const IconContainer = styled.div`
  flex-shrink: 0;
  background-color: rgba(239, 68, 68, 0.2);
  border-radius: 50%;
  padding: 0.75rem;
`;

const IconStyled = styled.div`
  width: 1.5rem;
  height: 1.5rem;
  color: #ef4444;
`;

const CardHeaderText = styled.div`
  margin-left: 1rem;
`;

const CardTitle = styled.h3`
  font-size: 1.125rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  margin: 0;
`;

const CardSubtitle = styled.p`
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin: 0.25rem 0 0;
`;

const CardDescription = styled.p`
  margin-top: 1rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
`;

const BadgeGroup = styled.div`
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
`;

interface BadgeProps {
  $color: string;
  $bgColor: string;
}

const Badge = styled.span<BadgeProps>`
  display: inline-flex;
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 0.25rem;
  background-color: ${props => props.$bgColor};
  color: ${props => props.$color};
`;

const ThreatBadge = styled.span<BadgeProps>`
  display: inline-flex;
  padding: 0.25rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 9999px;
  border: 1px solid transparent;
  background-color: ${props => props.$bgColor};
  color: ${props => props.$color};
`;

const CountryRow = styled.div`
  margin-top: 0.75rem;
  display: flex;
  align-items: center;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};

  svg {
    width: 1rem;
    height: 1rem;
    margin-right: 0.25rem;
  }
`;

const ExpandButton = styled.button`
  margin-top: 1rem;
  font-size: 0.875rem;
  color: ${variables.accentColorPositive};
  background: transparent;
  border: none;
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
`;

const TechniquesBox = styled.div`
  margin-top: 0.75rem;
  padding: 0.75rem;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
  border-radius: 0.5rem;
`;

const TechniquesTitle = styled.h4`
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
  margin: 0 0 0.5rem;
`;

const TechniquesList = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
`;

const TechniqueLink = styled.a`
  display: inline-flex;
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.25rem;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
  text-decoration: none;

  &:hover {
    background-color: ${pick({
      prisma: { dark: variables.backgroundColorHover, light: variables.backgroundColorHover },
    })};
  }
`;

const CardFooter = styled.div`
  padding: 0.75rem 1.25rem;
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorPage, light: variables.backgroundColorPage },
  })};
  border-top: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
`;

const CardLink = styled(Link)`
  font-size: 0.875rem;
  color: ${variables.accentColorPositive};
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
`;

const LoadingContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  height: 16rem;
`;

const Spinner = styled.div`
  width: 2rem;
  height: 2rem;
  border: 2px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-top-color: ${variables.accentColorPositive};
  border-radius: 50%;
  animation: spin 1s linear infinite;
`;

const ErrorBox = styled.div`
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 0.5rem;
  padding: 1rem;
  display: flex;
  align-items: center;
  color: #ef4444;

  svg {
    width: 1.25rem;
    height: 1.25rem;
    margin-right: 0.5rem;
  }
`;

const EmptyState = styled.div`
  background-color: ${pick({
    prisma: { dark: variables.backgroundColorSidebar, light: variables.backgroundColorSidebar },
  })};
  border: 1px solid ${pick({
    prisma: { dark: variables.borderColor, light: variables.borderColor },
  })};
  border-radius: 0.5rem;
  padding: 2rem;
  text-align: center;
`;

const EmptyIcon = styled.div`
  margin: 0 auto;
  width: 3rem;
  height: 3rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

const EmptyTitle = styled.h3`
  margin-top: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: ${pick({
    prisma: { dark: variables.contentColorDefault, light: variables.contentColorDefault },
  })};
`;

const EmptyText = styled.p`
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: ${pick({
    prisma: { dark: variables.contentColorMuted, light: variables.contentColorMuted },
  })};
`;

// ============================================================================
// Helper Components
// ============================================================================

const threatLevelOrder: Record<string, number> = {
  nation_state: 7,
  apt: 6,
  insider_threat: 5,
  organized_crime: 4,
  hacktivist: 3,
  opportunistic: 2,
  script_kiddie: 1,
};

const threatLevelColors: Record<string, { color: string; bgColor: string }> = {
  script_kiddie: { color: '#9ca3af', bgColor: 'rgba(156, 163, 175, 0.2)' },
  opportunistic: { color: '#eab308', bgColor: 'rgba(234, 179, 8, 0.2)' },
  organized_crime: { color: '#f97316', bgColor: 'rgba(249, 115, 22, 0.2)' },
  hacktivist: { color: '#a855f7', bgColor: 'rgba(168, 85, 247, 0.2)' },
  insider_threat: { color: '#ec4899', bgColor: 'rgba(236, 72, 153, 0.2)' },
  apt: { color: '#ef4444', bgColor: 'rgba(239, 68, 68, 0.2)' },
  nation_state: { color: '#dc2626', bgColor: 'rgba(220, 38, 38, 0.3)' },
};

const threatLevelLabels: Record<string, string> = {
  script_kiddie: 'Script Kiddie',
  opportunistic: 'Opportunistic',
  organized_crime: 'Organized Crime',
  hacktivist: 'Hacktivist',
  insider_threat: 'Insider Threat',
  apt: 'APT',
  nation_state: 'Nation State',
};

const motivationColors: Record<string, { color: string; bgColor: string }> = {
  financial: { color: '#22c55e', bgColor: 'rgba(34, 197, 94, 0.2)' },
  espionage: { color: '#3b82f6', bgColor: 'rgba(59, 130, 246, 0.2)' },
  disruption: { color: '#ef4444', bgColor: 'rgba(239, 68, 68, 0.2)' },
  ideology: { color: '#a855f7', bgColor: 'rgba(168, 85, 247, 0.2)' },
  notoriety: { color: '#eab308', bgColor: 'rgba(234, 179, 8, 0.2)' },
  revenge: { color: '#f97316', bgColor: 'rgba(249, 115, 22, 0.2)' },
};

function ThreatLevelBadge({ level }: { level: string }) {
  const { color, bgColor } = threatLevelColors[level] || { color: '#9ca3af', bgColor: 'rgba(156, 163, 175, 0.2)' };
  return (
    <ThreatBadge $color={color} $bgColor={bgColor}>
      {threatLevelLabels[level] || level}
    </ThreatBadge>
  );
}

function MotivationBadge({ motivation }: { motivation: string }) {
  const { color, bgColor } = motivationColors[motivation] || { color: '#9ca3af', bgColor: 'rgba(156, 163, 175, 0.2)' };
  return (
    <Badge $color={color} $bgColor={bgColor}>
      {motivation}
    </Badge>
  );
}

function ThreatActorCard({ actor }: { actor: ThreatActor }) {
  const [expanded, setExpanded] = useState(false);
  const { toPath } = useTenantPath();

  return (
    <Card>
      <CardContent>
        <CardHeader>
          <CardHeaderLeft>
            <IconContainer>
              <IconStyled as={UserGroupIcon} />
            </IconContainer>
            <CardHeaderText>
              <CardTitle>{actor.name}</CardTitle>
              <CardSubtitle>
                {actor.aliases.slice(0, 3).join(', ')}
                {actor.aliases.length > 3 && ` +${actor.aliases.length - 3} more`}
              </CardSubtitle>
            </CardHeaderText>
          </CardHeaderLeft>
          <ThreatLevelBadge level={actor.threat_level} />
        </CardHeader>

        <CardDescription>{actor.description}</CardDescription>

        <BadgeGroup>
          {actor.motivation.map((mot) => (
            <MotivationBadge key={mot} motivation={mot} />
          ))}
        </BadgeGroup>

        {actor.attributed_country && (
          <CountryRow>
            <GlobeAltIcon />
            <span>Attributed: {actor.attributed_country}</span>
          </CountryRow>
        )}

        <ExpandButton onClick={() => setExpanded(!expanded)}>
          {expanded ? 'Show less' : `View ${actor.techniques.length} techniques`}
        </ExpandButton>

        {expanded && (
          <TechniquesBox>
            <TechniquesTitle>MITRE ATT&CK Techniques</TechniquesTitle>
            <TechniquesList>
              {actor.techniques.map((tech) => (
                <TechniqueLink
                  key={tech}
                  href={`https://attack.mitre.org/techniques/${tech.replace('.', '/')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {tech}
                </TechniqueLink>
              ))}
            </TechniquesList>
          </TechniquesBox>
        )}
      </CardContent>

      <CardFooter>
        <CardLink to={toPath(`attacks/campaigns?threat_actor=${actor.id}`)}>
          View campaigns using this actor
        </CardLink>
      </CardFooter>
    </Card>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function ThreatActors() {
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('all');

  const { data: threatActors = [], isLoading, error } = useQuery({
    queryKey: ['threat-actors'],
    queryFn: attacksApi.listThreatActors,
  });

  const filteredActors = threatActors
    .filter((actor) => {
      if (levelFilter !== 'all' && actor.threat_level !== levelFilter) {
        return false;
      }
      if (search) {
        const searchLower = search.toLowerCase();
        return (
          actor.name.toLowerCase().includes(searchLower) ||
          actor.aliases.some((a) => a.toLowerCase().includes(searchLower)) ||
          actor.description.toLowerCase().includes(searchLower)
        );
      }
      return true;
    })
    .sort((a, b) => {
      return (threatLevelOrder[b.threat_level] || 0) - (threatLevelOrder[a.threat_level] || 0);
    });

  if (isLoading) {
    return (
      <LoadingContainer>
        <Spinner />
      </LoadingContainer>
    );
  }

  if (error) {
    return (
      <ErrorBox>
        <ExclamationTriangleIcon />
        <span>Failed to load threat actors</span>
      </ErrorBox>
    );
  }

  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>Threat Actors</PageTitle>
        <PageDescription>
          Browse adversary profiles from script kiddies to nation-state APTs
        </PageDescription>
      </PageHeader>

      {/* Filters */}
      <FilterCard>
        <FilterRow>
          <SearchContainer>
            <SearchIcon>
              <MagnifyingGlassIcon />
            </SearchIcon>
            <SearchInput
              type="text"
              placeholder="Search by name, alias, or description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </SearchContainer>
          <Select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
          >
            <option value="all">All Threat Levels</option>
            <option value="nation_state">Nation State</option>
            <option value="apt">APT</option>
            <option value="insider_threat">Insider Threat</option>
            <option value="organized_crime">Organized Crime</option>
            <option value="hacktivist">Hacktivist</option>
            <option value="opportunistic">Opportunistic</option>
            <option value="script_kiddie">Script Kiddie</option>
          </Select>
        </FilterRow>
      </FilterCard>

      {/* Results count */}
      <ResultsCount>
        Showing {filteredActors.length} of {threatActors.length} threat actors
      </ResultsCount>

      {/* Grid of cards */}
      {filteredActors.length === 0 ? (
        <EmptyState>
          <EmptyIcon as={UserGroupIcon} />
          <EmptyTitle>No threat actors found</EmptyTitle>
          <EmptyText>Try adjusting your search or filter criteria.</EmptyText>
        </EmptyState>
      ) : (
        <Grid>
          {filteredActors.map((actor) => (
            <ThreatActorCard key={actor.id} actor={actor} />
          ))}
        </Grid>
      )}
    </PageContainer>
  );
}
